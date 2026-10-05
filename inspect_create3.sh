#!/bin/bash
IP=10.60.189.52
for path in /ros-config /rmw-profile-override /ros-config-values /wifi-status /wifi /application /logs /beta; do
  echo "===== GET $path ====="
  curl -s -L "http://$IP$path" --max-time 6 -o "/root/create3_page.html" -w "HTTP %{http_code} | size %{size_download}\n"
  grep -iE 'domain|rmw|cyclone|fastrtps|fastdds|namespace|interface|profile|udp|multicast|value=|selected|checked|<title>' /root/create3_page.html | sed 's/<[^>]*>/ /g' | tr -s ' ' | head -30
  echo
done
