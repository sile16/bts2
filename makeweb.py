#!/usr/bin/python

import github
import pickle
import datetime
import os.path
import os
import time
import sys
from subprocess import call


def make_html(state,html_file):
    #make build_status.html 
    print "making the html code"
    print state
    #sorted_commits  = sorted(state['commits'], key=lambda k: k['commit'].commit.author.date, reverse=True)    

    with open(html_file,'w') as f:
        f.write('<table>')
        for c in state['commits']:
            f.write('<tr>')
            f.write('<td>%s</td><td>%s</td><td>%s</td>' % (c, str(state['commits'][c]['commit'].commit.author.date),str(state['commits'][c]['rc'])))
            f.write('</tr>')
        f.write('</table>')
        

    

def make_web():
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    lftp_cmds_file = '/root/sync_bts2edcrypto'

    log_dir = os.path.join(cur_dir,'build_logs/')
    state_file = os.path.join(log_dir,'build_state.pkl')
    html_file = os.path.join(log_dir,'build_state.html')


    if os.path.isfile(state_file):
        with open(state_file,'rb') as f:
            state = pickle.load(f)
    else:
        return
    
    #generate html
    make_html(state,html_file)

    
    #upload files
    with open (lftp_cmds_file, "r") as f:
        lftp_cmds = f.read().replace('\n','')

    cmd = ['/usr/bin/lftp', '-c']
    cmd.append(lftp_cmds) 
    call(cmd)



if __name__ == "__main__":
    make_web()
