#!/bin/bash
# À lancer quand app.medcare.sn → 195.35.2.116 uniquement et sans AAAA Hostinger
set -euo pipefail
EXPECTED="195.35.2.116"
echo "Vérification DNS app.medcare.sn…"
if dig +short app.medcare.sn A | grep -qv "$EXPECTED"; then
  echo "ERREUR: enregistrement A incorrect (attendu seulement $EXPECTED)."
  dig +short app.medcare.sn A
  exit 1
fi
if dig +short app.medcare.sn AAAA | grep -q .; then
  echo "ERREUR: supprimez l'enregistrement AAAA de app (Let's Encrypt valide en IPv6)."
  dig +short app.medcare.sn AAAA
  exit 1
fi
certbot certonly --webroot -w /var/www/html -d app.medcare.sn \
  --non-interactive --agree-tos --register-unsafely-without-email
NGINX_CONF=/etc/nginx/sites-available/apache-replacement-vhosts.conf
sed -i '/server_name app.medcare.sn;/,/ssl_certificate_key/ {
  s|/etc/letsencrypt/live/medcare.media-finder.com/|/etc/letsencrypt/live/app.medcare.sn/|g
}' "$NGINX_CONF"
nginx -t && systemctl reload nginx
echo "OK — certificat app.medcare.sn actif."
