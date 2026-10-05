#!/bin/bash
IP=10.60.189.52
echo "===== Home page (busca estado app/running) ====="
curl -s -L "http://$IP/" --max-time 6 | grep -iE 'running|stopped|application|status|state|uptime|error|not run' | sed 's/<[^>]*>/ /g' | tr -s ' ' | head -20
echo
echo "===== /logs (errores recientes) ====="
curl -s -L "http://$IP/logs" --max-time 6 -o /root/logs.html
grep -iE 'error|fail|not.*run|application|rmw|dds|start' /root/logs.html | sed 's/<[^>]*>/ /g' | tr -s ' ' | head -20
