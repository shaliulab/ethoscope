#! /bin/bash

ETHOSCOPE_DATABASE=$1

# generate index
# find ${ETHOSCOPE_DATABASE} -name "*db" | grep -v "PV" > index.txt

rm ${ETHOSCOPE_DATABASE}/validation.txt
touch ${ETHOSCOPE_DATABASE}/validation.txt

printf "#MISSING_FILE: The file is not available in the database\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
printf "#EMPTY: The file exists but it is completely empty (0KB)\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
printf "#MISSING_METADATA: The file is available but it has an empty or non existent METADATA table\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
printf "#MALFORMED: The file is not readatable\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
printf "#MISMATCH: The machine name encoded in the file's path does not match the machine name saved in the METADATA\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
printf "#OK: The file passed all checks\n" >> ${ETHOSCOPE_DATABASE}/validation.txt

while read -r line;
do
    PATH_MACHINE=""
    PATH_METADATA=""

    echo "##"
    echo $line

    PATH_MACHINE=$(echo $line | sed 's:'$ETHOSCOPE_DATABASE'::g' | cut -f 2 -d /)
    echo $PATH_MACHINE

    # This PRAGMA works but it's very slow
    #STATUS=$(sqlite3 $line 'PRAGMA integrity_check;' && echo "0" || echo "1")
    EXISTS=$(ls $line > /dev/null && echo "0" || echo "1" )
    FILE_SIZE=$(stat -c %s $line)
    STATUS=$(sqlite3 $line '.tables' > /dev/null && echo "0" || echo "1")
    PATH_METADATA=$(sqlite3 $line 'SELECT value FROM METADATA WHERE field = "machine_name";' || echo "MISSING")
    if [ $PATH_METADATA -z ]
    then
        PATH_METADATA="MISSING"
    fi

    echo "##"

    echo $STATUS
    if [ $EXISTS == "1" ]
    then
        printf "$line\tMISSING_FILE\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    elif [ $FILE_SIZE -eq 0 ]
    then
        printf "$line\tEMPTY\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    elif [ $STATUS == "1" ]
    then
        printf "$line\tMALFORMED\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    elif [ $PATH_METADATA == "MISSING" ]
    then
        printf "$line\tMISSING_METADATA\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    elif [ $PATH_MACHINE == $PATH_METADATA ]
    then
        printf "$line\tOK\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    else
        printf "$line\tMISMATCH\n" >> ${ETHOSCOPE_DATABASE}/validation.txt
    fi

done < index.txt

