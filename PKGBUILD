# Maintainer: Tommi <tommi@users.noreply.github.com>
pkgname=tapo-p115-control
pkgver=1.0.0
pkgrel=1
pkgdesc="A GUI application to control Tapo P115 smart plugs"
arch=('any')
url="https://github.com/tommi/tapo-p115-control"
license=('MIT')
depends=('python' 'pyside6' 'python-aiohttp' 'python-qasync' 'python-plugp100')
makedepends=('python-setuptools')
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
  cd "$pkgname-$pkgver"
  
  # Install the main script
  install -Dm755 main.py "$pkgdir/usr/share/$pkgname/main.py"
  
  # Create a launcher in /usr/bin
  mkdir -p "$pkgdir/usr/bin"
  cat <<EOF > "$pkgdir/usr/bin/$pkgname"
#!/bin/bash
exec python /usr/share/$pkgname/main.py "\$@"
EOF
  chmod 755 "$pkgdir/usr/bin/$pkgname"

  # Install desktop entry
  install -Dm644 /dev/stdin "$pkgdir/usr/share/applications/$pkgname.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Tapo P115 Control
Comment=$pkgdesc
Exec=$pkgname
Icon=utilities-terminal
Terminal=false
Categories=Utility;
EOF
}
