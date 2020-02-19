SLURM=0
FILENAME=''
DEFAULT=''
while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -s|--slurm)
    SLURM=1
    ;;
    -f|--file)
    FILENAME="$2"
    shift # past argument
    ;;
    --default)
    DEFAULT=YES
    ;;
    *)
            # unknown option
    ;;
esac
shift # past argument or value
done
echo Add Slurm Account   = "${SLURM}"
echo FILENAME      = "${FILENAME}"

#input file is in the form:
#username First Last
INFILE=${FILENAME}

while IFS='' read -r line; do
   IFS=" " read -ra ACCOUNT <<< "$line"
   user=${ACCOUNT[0]}
   password="changeme"
   pass=$(perl -e 'print crypt($ARGV[0], "password")' $password)

  echo "Creating account for $user"
  useradd -m -p $pass $user
  pdsh "useradd -m -p $pass $user"
  #force reset on login
  chage -d 0 $user
  #useradd -m -p $pass $user

  #become user to create home directory
  sudo su - $user "exit"
  #generate ssh-keys
  sudo -u $user  ssh-keygen -N "" -t rsa -f /home/$user/.ssh/id_rsa
  sudo -u $user  cat /home/$user/.ssh/id_rsa.pub > /home/$user/.ssh/authorized_keys
  chown $user:$user /home/$user/.ssh/authorized_keys
  sudo -u $user  chmod 0644 /home/$user/.ssh/authorized_keys

done < $INFILE

