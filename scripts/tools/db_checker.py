import argparse
import sqlite3
import datetime

def get_parser():

    ap = argparse.ArgumentParser()
    ap.add_argument("--dbfile")
    return ap

def main():

    ap = get_parser()
    args = ap.parse_args()

    get_last_time_of_rois(args.dbfile)


def get_last_time_of_rois(dbfile):

    connection=sqlite3.connect(dbfile)
    cur=connection.cursor()

    cur.execute("SELECT value FROM METADATA WHERE field = 'date_time'")
    row = cur.fetchone()
    start_time = float(row[0])


    for roi in range(1, 21):

        cmd = f"SELECT t FROM ROI_{roi} ORDER BY id DESC LIMIT 1;"
        try:
            cur.execute(cmd)
            row = cur.fetchone()
            last_time = row[0]
            last_time /= 1000
            timestamp = start_time + last_time
            print(f"ROI_{roi}: ", datetime.datetime.fromtimestamp(timestamp))

        except Exception as error:
            print(error)
            print(f"ROI_{roi} not found")
            pass




if __name__ == "__main__":
    main()
