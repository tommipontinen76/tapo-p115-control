import sys
import asyncio
import logging
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QFormLayout, QMessageBox,
    QGroupBox, QGridLayout, QCheckBox, QComboBox, QStyleFactory
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QSettings, QDateTime
import aiohttp
from qasync import QEventLoop, asyncSlot

from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from plugp100.common.credentials import AuthCredential
from plugp100.new.components.energy_component import EnergyComponent

class TapoControlApp(QMainWindow):
    # Signals to communicate between background logic and UI
    status_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tapo P115 Control (KLAP Support)")
        self.setMinimumSize(400, 550)

        self.device = None
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_device_status)
        
        self.spot_price = 0.0
        self.spot_price_last_update = None
        
        self.vat_rate = 25.5
        self.elec_tax = 2.253

        self.init_ui()
        self.load_settings()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Login Area
        login_group = QGroupBox("Device Connection")
        login_layout = QFormLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("e.g., 192.168.1.50")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Tapo account email")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Tapo account password")

        login_layout.addRow("Device IP:", self.ip_input)
        login_layout.addRow("Email:", self.email_input)
        login_layout.addRow("Password:", self.password_input)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("e.g., 15")
        login_layout.addRow("Price per kWh (cents):", self.price_input)

        self.margin_input = QLineEdit()
        self.margin_input.setPlaceholderText("e.g., 0.5")
        login_layout.addRow("Margin (c/kWh):", self.margin_input)

        self.distribution_input = QLineEdit()
        self.distribution_input.setPlaceholderText("e.g., 5.0")
        login_layout.addRow("Distribution (c/kWh):", self.distribution_input)

        self.tax_input = QLineEdit()
        self.tax_input.setPlaceholderText("e.g., 25.5")
        login_layout.addRow("Tax (%):", self.tax_input)

        self.elec_tax_input = QLineEdit()
        self.elec_tax_input.setPlaceholderText("e.g., 2.253")
        login_layout.addRow("Elec. Tax (c/kWh):", self.elec_tax_input)

        self.auto_tax_checkbox = QCheckBox("Auto-fetch Taxes (VAT & Elec. Tax)")
        self.auto_tax_checkbox.toggled.connect(self.toggle_tax_input)
        login_layout.addRow(self.auto_tax_checkbox)

        self.spot_price_checkbox = QCheckBox("Use Spot Price (api.porssisahko.net)")
        self.spot_price_checkbox.toggled.connect(self.toggle_price_input)
        login_layout.addRow(self.spot_price_checkbox)

        if sys.platform == "linux":
            self.style_combo = QComboBox()
            available_styles = QStyleFactory.keys()
            # On Linux, try to prioritize GTK styles for Gnome/Cinnamon environments
            if "GTK+" in available_styles:
                # Reorder to put GTK+ first if available
                available_styles.remove("GTK+")
                available_styles.insert(0, "GTK+")
            elif "gtk2" in available_styles:
                 available_styles.remove("gtk2")
                 available_styles.insert(0, "gtk2")
                 
            self.style_combo.addItems(available_styles)
            # Try to find a good default or what's currently set
            current_style = QApplication.style().objectName().lower()
            for i in range(self.style_combo.count()):
                if self.style_combo.itemText(i).lower() == current_style:
                    self.style_combo.setCurrentIndex(i)
                    break
            
            self.style_combo.currentIndexChanged.connect(self.change_style)
            login_layout.addRow("UI Style:", self.style_combo)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_device)
        login_layout.addRow(self.connect_button)

        login_group.setLayout(login_layout)
        layout.addWidget(login_group)

        # Control Area
        self.control_group = QGroupBox("Control & Status")
        self.control_group.setEnabled(False)
        control_layout = QVBoxLayout()

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        control_layout.addWidget(self.status_label)

        self.toggle_button = QPushButton("Turn ON")
        self.toggle_button.setFixedHeight(50)
        self.toggle_button.clicked.connect(self.toggle_power)
        control_layout.addWidget(self.toggle_button)

        # Energy Monitoring Area
        energy_group = QGroupBox("Energy Monitoring")
        energy_layout = QGridLayout()

        self.power_label = QLabel("Current Power: - kW")
        self.today_energy_label = QLabel("Today's Energy: - kWh")
        self.month_energy_label = QLabel("Month Energy: - kWh")
        self.today_cost_label = QLabel("Today's Cost: -")
        self.price_source_label = QLabel("Price Source: -")

        energy_layout.addWidget(self.power_label, 0, 0)
        energy_layout.addWidget(self.today_energy_label, 1, 0)
        energy_layout.addWidget(self.month_energy_label, 2, 0)
        energy_layout.addWidget(self.today_cost_label, 3, 0)
        energy_layout.addWidget(self.price_source_label, 4, 0)

        energy_group.setLayout(energy_layout)
        control_layout.addWidget(energy_group)

        self.control_group.setLayout(control_layout)
        layout.addWidget(self.control_group)

        # Signal connections
        self.status_updated.connect(self.update_ui_with_status)
        self.error_occurred.connect(self.show_error)

    @asyncSlot()
    async def connect_device(self):
        ip = self.ip_input.text()
        email = self.email_input.text()
        password = self.password_input.text()

        if not ip or not email or not password:
            QMessageBox.warning(self, "Missing Info", "Please fill in all fields.")
            return

        self.connect_button.setEnabled(False)
        self.connect_button.setText("Connecting...")
        self.save_settings()

        try:
            config = DeviceConnectConfiguration(host=ip, credentials=AuthCredential(email, password))
            # connect() automatically guesses the protocol (Passthrough or KLAP)
            self.device = await connect(config)
            
            # Initial update to fetch components and state
            await self.device.update()
            
            await self.refresh_device_status()
            self.update_timer.start(5000) # Every 5 seconds

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            if "Invalid authentication" in error_msg:
                error_msg += ("\n\nTips:\n"
                             "1. Check if the IP address is correct.\n"
                             "2. Verify your Tapo email and password.\n"
                             "3. Ensure the device is powered on and on the same network.\n"
                             "4. Some newer firmware versions might have stricter security.")
            self.error_occurred.emit(error_msg)
            self.device = None

    def load_settings(self):
        settings = QSettings("TapoP115Control", "TapoControlApp")
        self.ip_input.setText(str(settings.value("ip", "")))
        self.email_input.setText(str(settings.value("email", "")))
        self.password_input.setText(str(settings.value("password", "")))
        self.price_input.setText(str(settings.value("price", "0.0")))
        self.margin_input.setText(str(settings.value("margin", "0.0")))
        self.distribution_input.setText(str(settings.value("distribution", "0.0")))
        self.tax_input.setText(str(settings.value("tax", "25.5")))
        self.elec_tax_input.setText(str(settings.value("elec_tax", "2.253")))
        
        auto_tax = settings.value("auto_tax", "false") == "true"
        self.auto_tax_checkbox.setChecked(auto_tax)
        self.toggle_tax_input(auto_tax)

        use_spot = settings.value("use_spot", "false") == "true"
        self.spot_price_checkbox.setChecked(use_spot)
        self.toggle_price_input(use_spot)

        if sys.platform == "linux" and hasattr(self, 'style_combo'):
            saved_style = settings.value("ui_style", "")
            if saved_style:
                index = self.style_combo.findText(saved_style)
                if index >= 0:
                    self.style_combo.setCurrentIndex(index)
                    QApplication.setStyle(saved_style)

    def save_settings(self):
        settings = QSettings("TapoP115Control", "TapoControlApp")
        settings.setValue("ip", self.ip_input.text())
        settings.setValue("email", self.email_input.text())
        settings.setValue("password", self.password_input.text())
        settings.setValue("price", self.price_input.text())
        settings.setValue("margin", self.margin_input.text())
        settings.setValue("distribution", self.distribution_input.text())
        settings.setValue("tax", self.tax_input.text())
        settings.setValue("elec_tax", self.elec_tax_input.text())
        settings.setValue("auto_tax", "true" if self.auto_tax_checkbox.isChecked() else "false")
        settings.setValue("use_spot", "true" if self.spot_price_checkbox.isChecked() else "false")
        if sys.platform == "linux" and hasattr(self, 'style_combo'):
            settings.setValue("ui_style", self.style_combo.currentText())

    def change_style(self):
        style_name = self.style_combo.currentText()
        QApplication.setStyle(style_name)
        self.save_settings()

    def toggle_price_input(self, checked):
        self.price_input.setEnabled(not checked)

    def toggle_tax_input(self, checked):
        self.tax_input.setEnabled(not checked)
        self.elec_tax_input.setEnabled(not checked)

    async def fetch_spot_price(self):
        """Fetch current electricity spot price for Finland."""
        try:
            url = "https://api.porssisahko.net/v1/latest-prices.json"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        prices = data.get("prices", [])
                        
                        # Find the price for the current hour
                        now = QDateTime.currentDateTimeUtc()
                        for p in prices:
                            start = QDateTime.fromString(p["startDate"], Qt.DateFormat.ISODate)
                            end = QDateTime.fromString(p["endDate"], Qt.DateFormat.ISODate)
                            if start <= now < end:
                                # Price is in c/kWh (cent)
                                self.spot_price = p["price"]
                                self.spot_price_last_update = QDateTime.currentDateTime()
                                return True
        except Exception as e:
            print(f"Spot price fetch error: {e}")
        return False

    async def fetch_taxes(self):
        """
        Fetch current taxes (VAT and Electricity Tax) for Finland.
        Currently uses reliable static values as there is no single simple API, 
        but could be updated to fetch from a source if one becomes available.
        """
        # Current Finnish VAT as of Sept 2024 is 25.5%
        # Electricity tax (Category I) is 2.253 c/kWh (including 25.5% VAT)
        self.vat_rate = 25.5
        self.elec_tax = 2.253
        return True

    @asyncSlot()
    async def refresh_device_status(self):
        if not self.device:
            return
        
        # Periodically refresh spot price if needed
        if self.spot_price_checkbox.isChecked():
            now = QDateTime.currentDateTime()
            should_update = (self.spot_price_last_update is None or 
                             self.spot_price_last_update.addSecs(900) < now or 
                             self.spot_price_last_update.time().hour() != now.time().hour())
            if should_update:
                await self.fetch_spot_price()
        
        # Refresh taxes if needed
        if self.auto_tax_checkbox.isChecked():
            await self.fetch_taxes()

        try:
            await self.device.update()
            
            # Extract power and energy from EnergyComponent if it exists
            status_data = {
                'device_on': self.device.is_on,
                'current_power': 0,
                'today_energy': 0,
                'month_energy': 0
            }

            energy_comp = self.device.get_component(EnergyComponent)
            if energy_comp and energy_comp.energy_info:
                # energy_info properties are already in W and kWh usually in this library
                # current_power is in W
                # today_energy is in kWh
                status_data['current_power'] = energy_comp.energy_info.current_power or 0
                status_data['today_energy'] = (energy_comp.energy_info.today_energy or 0) / 1000.0 # Lib might return Wh
                status_data['month_energy'] = (energy_comp.energy_info.month_energy or 0) / 1000.0
                
                # Double check scaling. plugp100 usually returns Wh for energy and W for power.
                # Actually let's check the energy_info values.
                # If they are very large, they are Wh.
            
            self.status_updated.emit(status_data)
        except Exception as e:
            print(f"Refresh error: {e}")

    @Slot(dict)
    def update_ui_with_status(self, data):
        self.control_group.setEnabled(True)
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connected")
        
        is_on = data['device_on']
        self.status_label.setText(f"Status: {'ON' if is_on else 'OFF'}")
        self.status_label.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {'green' if is_on else 'red'};")
        self.toggle_button.setText("Turn OFF" if is_on else "Turn ON")
        
        # Power from Watts to kW
        power_kw = data['current_power'] / 1000.0
        self.power_label.setText(f"Current Power: {power_kw:.3f} kW")
        
        today_energy = data['today_energy']
        self.today_energy_label.setText(f"Today's Energy: {today_energy:.2f} kWh")
        self.month_energy_label.setText(f"Month Energy: {data['month_energy']:.2f} kWh")

        # Electricity price calculation
        if self.spot_price_checkbox.isChecked():
            base_price = self.spot_price
            self.price_source_label.setText(f"Price Source: Spot ({base_price:.2f} c/kWh)")
        else:
            try:
                base_price = float(self.price_input.text())
            except ValueError:
                base_price = 0.0
            self.price_source_label.setText(f"Price Source: Manual ({base_price:.2f} c/kWh)")

        try:
            margin = float(self.margin_input.text() or 0)
            distribution = float(self.distribution_input.text() or 0)
            
            if self.auto_tax_checkbox.isChecked():
                tax_rate = self.vat_rate
                elec_tax = self.elec_tax
            else:
                tax_rate = float(self.tax_input.text() or 0)
                elec_tax = float(self.elec_tax_input.text() or 0)
        except ValueError:
            margin = 0.0
            distribution = 0.0
            tax_rate = 0.0
            elec_tax = 0.0

        # Total price per kWh: (Market/Base Price + Margin + Distribution + Elec. Tax) * (1 + Tax / 100)
        # Note: In Finland, electricity tax is usually quoted WITH VAT, but for consistency 
        # with the manual tax percentage field, we apply VAT to the sum.
        # Actually, if the user provides Elec. Tax and Tax %, we should be careful.
        # Most people in Finland see "2.253 c/kWh" which ALREADY includes VAT.
        # If they use the "Auto" values, we use 2.253 as elec_tax and 25.5 as VAT.
        # Wait, if 2.253 ALREADY includes VAT, then:
        # Total = (Base + Margin + Distribution) * (1 + VAT/100) + ElecTax
        # OR 
        # Total = (Base + Margin + Distribution + ElecTax_Excl_VAT) * (1 + VAT/100)
        
        # Let's assume the "Elec. Tax" field is EXCLUDING VAT if we apply VAT on top.
        # 2.253 / 1.255 = 1.795 c/kWh (tax without VAT).
        
        if self.auto_tax_checkbox.isChecked():
            # Standard Finnish values:
            # Sähkövero 1.795217 c/kWh (cat I excl VAT)
            # ALV 25.5%
            # Resulting in ~2.253 c/kWh total for the tax part.
            tax_rate = 25.5
            elec_tax_excl_vat = 1.795217
        else:
            tax_rate = float(self.tax_input.text() or 0)
            # We treat the manual elec_tax input as EXCLUDING VAT if we apply VAT on top.
            elec_tax_excl_vat = float(self.elec_tax_input.text() or 0)

        total_price_per_kwh_cents = (base_price + margin + distribution + elec_tax_excl_vat) * (1 + tax_rate / 100.0)
        
        today_cost = today_energy * (total_price_per_kwh_cents / 100.0) # Calculate cost in Euros
        self.today_cost_label.setText(f"Today's Cost: {today_cost:.2f} €")
        
        # You can add the total price as tooltip or update label for more info
        self.price_source_label.setToolTip(f"Total: {total_price_per_kwh_cents:.2f} c/kWh (incl. fees & taxes)")

    @asyncSlot()
    async def toggle_power(self):
        if not self.device:
            return
        
        try:
            if self.device.is_on:
                # Add confirmation for turning OFF
                reply = QMessageBox.question(self, "Confirm Turn OFF",
                                           "Are you sure you want to turn the power OFF?",
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                           QMessageBox.StandardButton.No)
                if reply == QMessageBox.StandardButton.No:
                    return
                await self.device.turn_off()
            else:
                await self.device.turn_on()
            await self.refresh_device_status()
        except Exception as e:
            self.error_occurred.emit(f"Toggle failed: {str(e)}")

    @Slot(str)
    def show_error(self, message):
        self.connect_button.setEnabled(True)
        self.connect_button.setText("Connect")
        QMessageBox.critical(self, "Error", message)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = TapoControlApp()
    window.show()
    
    with loop:
        loop.run_forever()
