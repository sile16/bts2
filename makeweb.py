#!/usr/bin/python

import github
import pickle
import datetime
import os.path
import os
import time
import sys
from subprocess import call



def make_web():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    lftp_cmds_file = '/root/sync_bts2edcrypto'

    log_dir = os.path.join(cur_dir,'build_logs/')
    state_file = os.path.join(log_dir,'build_state.pkl')
    html_file = os.path.join(log_dir,'build_state.html')


    #make build_status.html 
    print "making the html code"

	



    #upload files
    with open (lftp_cmds_file, "r") as f:
        lftp_cmds = f.read().replace('\n','')

    cmd = ['/usr/bin/lftp', '-c']
    cmd.append(lftp_cmds) 
    call(cmd)





if __name__ == "__main__":
    make_web()
