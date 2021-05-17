#!/bin/bash

if [ $# -lt 1 ] ; then
    echo -e "\nNeed mapping file\n"
    echo -e "e.g. $(basename $0) mapping.csv\n"
    exit 1
fi

MAPPING=$1

if [ ! -e $MAPPING ] ; then
    echo -e "\nMapping file $MAPPING does not exist\n"
    exit 1
fi

if [ ! -d profiles ] ; then
	mkdir profiles
fi

echo -e "#!/bin/bash\n" > profiles/addall.sh

for profile in $(cat $MAPPING | grep -v ^MAC) ; do

    MAC=$(echo $profile | cut -d "," -f 1 )
    HOSTNAME=$(echo $profile | cut -d "," -f 2 )
    IPADDR=$(echo $profile | cut -d "," -f 3 )
    OUTFILE=${HOSTNAME}.sh

    cat template.sh \
    | sed -e "s/^HOSTNAME=/HOSTNAME=\"$HOSTNAME\"/" \
    -e "s/^IPADDR=/IPADDR=\"$IPADDR\"/" \
    -e "s/^MAC=/MAC=\"$MAC\"/" > profiles/$OUTFILE

    echo "./$OUTFILE" >> profiles/addall.sh

    chmod 755 profiles/$OUTFILE

done

echo -e "\ncobbler sync\n" >> profiles/addall.sh

chmod 755 profiles/addall.sh


