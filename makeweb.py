#!/usr/bin/python

import github
import pickle
import datetime
from dateutil import tz
import os.path
import os
import time
import sys
from subprocess import call

def headers(f,headers,span=None):
    for header in headers:
        if span:     
            f.write('<th colspan="%d">%s</th>' % (span,str(header)) )
        else:
            f.write('<th>%s</th>' % str(header) )

def cell(f,color,msg):
    if color is None:
        color = 'AliceBlue'
    f.write('<td bgcolor="%s">%s</td>' % (color,str(msg)) )

def make_html(state,html_file):
    #make build_status.html 
    print "making the html code"
    #print state
    #sorted_commits  = sorted(state['commits'], key=lambda k: k['commit'].commit.author.date, reverse=True)    

    with open(html_file,'w') as f:
        f.write('<table border="1">')

        f.write('<tr>')
        headers(f,[''],4)
        headers(f,['Test Duration (s) or Fail'],4)
        headers(f,[''],4)
        f.write('</tr>\n')
        f.write('<tr>')
        headers(f,['Tag (sha)','commit','author','Docker Date','app', 'chain', 'intense', 'perf','avatar','author','msg','logs'])
        f.write('</tr>\n')


        sorted_commits  = sorted(state['commits'], 
                                 key=lambda k: ( state['commits'][k]['commit'].commit.committer.date,
                                                 state['commits'][k]['commit'].commit.author.date ), 
                                 reverse=True)
        for sha in sorted_commits:
            build = state['commits'][sha]
            c = build['commit']
            f.write('<tr>')
            

            push_date = None
            if build['rc']['cli'] == 0 and build['rc']['witness'] == 0:
               if 'docker_push_date' in build:
                   build_color = 'LightGreen'
                   #minus 1 hour to go from CST -> EST
                   push_date = build['docker_push_date'] - datetime.timedelta(hours=1)
               else:
                   build_color = 'AliceBlue'
            else:
                build_color = 'OrangRed'
            
            if build['tag']:
                tag = '{} ({})'.format(build['tag'],sha[0:5])
            else:
                tag = sha[0:7]

            from_utc = tz.gettz('UTC')
            to_est = tz.gettz('America/New_York')


            cell(f,build_color,'<a href="%s">%s</a>' % (c.html_url, tag) )
            cell(f,build_color,c.commit.committer.date.replace(tzinfo=from_utc).astimezone(to_est).strftime("%m-%d %H:%M"))
            cell(f,build_color,c.commit.author.date.replace(tzinfo=from_utc).astimezone(to_est).strftime("%m-%d %H:%M"))
            cell(f,build_color,push_date.strftime("%m-%d %H:%M") if push_date else "None")            

            if 'tests' in build:
                for t in sorted(build['tests']):
                    test_log_file = str(sha + '/' + t + '.txt')
                    
                    if build['tests'][t]['rc'] == 0:
                        t_color = 'LightGreen'
                        msg = "{:.1f}s".format(build['tests'][t]['duration'])
                    else:
                        t_color = 'OrangeRed'
                        log_dir = os.path.dirname(html_file)
                        last_line = ""
                        msg = "-- failed"
                        with open(os.path.join(log_dir,test_log_file)) as test_f:
                            for line in test_f:
                                last_line = line
                        if '***' in last_line:
                            msg = last_line.split()[1] + ' failed'
                    
                    cell(f,t_color, '<a href="{}">{}</a>'.format(test_log_file, msg ))
            else:
                cell(f,'OrangeRed',"--")
                cell(f,'OrangeRed',"--")
                cell(f,'OrangeRed',"--")
                cell(f,'OrangeRed',"--")

            cell(f,None,'<img src="%s"/ height="42" width="42">' % c.author.avatar_url )
            cell(f,build_color,c.commit.author.name)
            cell(f,build_color,c.commit.message )
            cell(f,build_color,'<a href="%s/build.txt">logs</a>' % sha) 
                
            f.write('</tr>\n')

        f.write('</table>\n')
        

    

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
