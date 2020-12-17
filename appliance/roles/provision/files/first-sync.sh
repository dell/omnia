
 timeout=30
while ! netstat -laputen | grep -i listen | grep 25151 1>/dev/null 2>&1
do
  sleep 1
  timeout=$((${timeout} - 1))
  if [ ${timeout} -eq 0 ]
  then
    echo "ERROR: cobblerd is not running."
    exit 1
  fi
done
sleep 2
echo "cobbler get-loaders"
cobbler get-loaders
echo "cobbler sync"
cobbler sync
echo "cobbler check"
cobbler check
