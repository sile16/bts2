#!/usr/bin/python

import github
import pickle
import datetime
import os.path
import os
import time
import sys
from subprocess import call
import shutil
import makeweb

cur_dir = os.path.dirname(os.path.realpath(__file__))
home_dir = os.path.expanduser("~")
git_dir = '/tmp'
lftp_cmds_file = '/root/sync_bts2edcrypto'


docker_cmd = 'docker run --rm -v '+git_dir+':/build sile16/graphene-build '

log_dir = os.path.join(cur_dir,'build_logs/')
state_file = os.path.join(log_dir,'build_state.pkl')
test_dir = os.path.join(git_dir,'graphene/tests')
github_api_key_file = os.path.join(home_dir,'github_api.key')

state = {}

def save_state():
    global state
    with open(state_file,'wb') as f:
        pickle.dump( state , f ) 

def run_tests(sha):
    global state
    tests = ['app_test','chain_test', 'intense_test', 'performance_test']
    state['commits'][sha]['tests'] = {}    

    for t in tests:
        cmd = os.path.join(test_dir,t)
        with open(os.path.join(log_dir,sha,t+'.log'), "w") as f:     
            start = time.time()
            rc = call(cmd.split(),stdout=f, stderr=f)
            duration = time.time() - start
        
        state['commits'][sha]['tests'][t] = {'rc':rc, 'duration':duration}
        print "%s   %s  rc=%d   time=%f" % (sha, t, rc, duration)
    
    save_state()


def build_docker(tag):
    bin_dir = os.path.join(git_dir,'graphene/programs')
    docker_dir = os.path.join(cur_dir,'Docker')

    docker_bins = {'graphene-cli':'cli_wallet', 
               'graphene-witness':'witness_node'}

    for d in docker_bins:
       d_dir = os.path.join(docker_dir,d)
       bin_file_src = os.path.join(bin_dir, docker_bins[d], docker_bins[d])
       bin_file_dst = os.path.join(d_dir,docker_bins[d])
       print 'bin_file:%s d_dir:%s' % (bin_file_src,d_dir)
       shutil.copyfile(bin_file_src,bin_file_dst)

       #commands for updating the root image
       cmds = [ 
         'docker build -t sile16/%s %s' % (d, d_dir),
         'docker push sile16/%s:latest' % (d)]

       #commands for also taggin this image
       if(tag):
         cmds.append('docker tag sile16/%s sile16/%s:%s' % (d,d,tag))
         cmds.append('docker push sile16/%s:%s' % (d,tag) )

       for c in cmds:
           print 'running: %s' % c
           call(c.split())
       

    #call('docker build -t sile16/graphene-witness graphene-witness'.split())
    #call('docker push sile16/graphene-witness'.split())
    #call(str('docker tag sile16/graphene-witness sile16/graphene-witness:'+str(tag)).split())
    #call(str('docker push sile16/graphene-witness:'+str(tag)).split())

def build(commit, tag = None, last = False ):
    global state
    sha = commit.sha

    #create output directory
    if not os.path.exists(os.path.join(log_dir,sha)):
        os.makedirs( os.path.join(log_dir,sha))

    #create symlink if a tag, and generate build cmd using sha or tag
    if tag:
        os.symlink(os.path.join(log_dir,tag), os.path.join(log_dir,sha))
        state['tags'][tag] = {'sha':sha }
        cmd = docker_cmd + tag
    else: 
        cmd = docker_cmd + sha
    
    #actually run the build
    logfile = os.path.join(log_dir,sha,'build.log')  
    with open(logfile, "w") as f:     
        rc = call(cmd.split(),stdout=f, stderr=f)

    #save build results
    raw_commit = commit.raw_data
    raw_commit.pop('files')
    state['commits'][sha] = {'rc':rc, 'commit':commit}
    state['last_commit_date'] = commit.commit.author.date
    save_state()

    #If build is success run tests
    if(rc == 0):
        run_tests(sha)
        
        #if it's a tag lets make a link and push a docker runtime image
        td = datetime.datetime.now() - state['docker_push_date']
        if(tag or td.days > 1):
            build_docker(tag)
            state['docker_push_date'] = datetime.datetime.now()
            state['commits'][sha]['docker'] = datetime.datetime.now()
            save_state()
        
    makeweb.make_web()
            
            
    
def check_github(repo):
    global state

    #Look for unbuilt tags
    print ("Looking for new tags")
    tags = list(repo.get_tags())
    for t in tags:
        if t.name not in state['tags']:
            print("Found new tag, building: " + str(t.name))
            commit = repo.get_commit(t.commit.sha)
            build(commit, tag=t.name)
    
    #look for new commits
    print("looking for new commits")
    commits = list(repo.get_commits( since=state['last_commit_date'] ))
    
    #go newest to oldest
    sorted_commits  = sorted(commits, key=lambda k: k.commit.author.date, reverse=True)
    for c in sorted_commits: 
        print "%s : %s : %s" % (c.sha, c.commit.author.name, c.commit.author.date)
        if c.sha not in state['commits']:
            print("Found new commit, building: " + str(c.sha))
            build(c)


def main():
    global state

    if os.path.isfile(state_file):
        with open(state_file,'rb') as f:
            state = pickle.load(f)
    else:
        state = {'last_commit_date': datetime.datetime.now() - datetime.timedelta(hours = 96) }
        state['tags'] = {}
        state['commits'] = {}
        state['docker_push_date'] = datetime.datetime.now() - datetime.timedelta(days=100)

    #pop off a build to rebuild for testing
    #state['commits'].pop('13d83904c9e063b2a22cbfc717e988bab1215505')

    #Setup github and read api key from file '~/github_api.key'
    with open (github_api_key_file, "r") as f:
        api_key = f.read().replace('\n','') 

    g = github.Github(api_key)
    repo = g.get_repo("cryptonomex/graphene")

    #loop forever, check every 5 minutes for changes
    while True:
       check_github(repo)
       for x in range(1,30):
           time.sleep(10)
           sys.stdout.write('.')
           sys.stdout.flush()


if __name__ == "__main__":
    main()

