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
        with open(os.path.join(log_dir,sha,t+'.txt'), "w") as f:     
            start = time.time()
            rc = call(cmd.split(),stdout=f, stderr=f)
            duration = time.time() - start
        
        state['commits'][sha]['tests'][t] = {'rc':rc, 'duration':duration}
        print "%s   %s  rc=%d   time=%f" % (sha, t, rc, duration)
    
    save_state()

def delete_bins():
    #cleanup binaries so on failed build old binary isn't mistakenly used.
    programs = ['cli_wallet','witness_node']
    tests = ['app_test','chain_test', 'intense_test', 'performance_test']

    files = [os.path.join(git_dir,'graphene','programs',p) for p in programs]
    files += [os.path.join(test_dir,t) for t in tests]

    for f in files:
        try:
            os.remove(f)
        except OSError:
            pass

def docker_push(tag):
    global state
    td = datetime.datetime.now() - state['docker_push_date']
    #print("tag: %s td.days: %d" % (tag, td.days))

    #check to see if this build has already been pushed
    sha = state['docker_build_sha']
    if 'docker_push_date' in state['commits'][sha]:
        return

    if tag or td.days > 0:
        docker_dir = os.path.join(cur_dir,'Docker')
        dockers = ['graphene-cli','graphene-witness']

        for d in dockers:
           #commands for updating the root image
           cmds = [ 'docker push sile16/%s' % (d)]

           #commands for also taggin this image
           if(tag):
               cmds.append('docker tag sile16/%s sile16/%s:%s' % (d,d,tag))
               cmds.append('docker push sile16/%s:%s' % (d,tag) )

           for c in cmds:
               print 'running: %s' % c
               call(c.split())

        state['commits'][sha]['docker_push_date'] = datetime.datetime.now()
        state['docker_push_date'] = datetime.datetime.now()
        save_state()


def docker_build(tag):
    global state
    bin_dir = os.path.join(git_dir,'graphene/programs')
    docker_dir = os.path.join(cur_dir,'Docker')

    docker_bins = {'graphene-cli':'cli_wallet', 
               'graphene-witness':'witness_node'}

    for d in docker_bins:
       d_dir = os.path.join(docker_dir,d)
       bin_file_src = os.path.join(bin_dir, docker_bins[d], docker_bins[d])
       bin_file_dst = os.path.join(d_dir,docker_bins[d])
       try:
           os.remove(bin_file_dst)
       except OSError:
           pass
       print 'bin_file:%s d_dir:%s' % (bin_file_src,d_dir)
       shutil.copyfile(bin_file_src,bin_file_dst)
       os.chmod(bin_file_dst,493)  #755 in octocal is 493 is base 10

       #commands for updating the root image
       cmd = 'docker build -t sile16/%s %s' % (d, d_dir)

       print 'running: %s' % cmd
       call(cmd.split())

    docker_push(tag)
       
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

    #delete existing binaries
    delete_bins()
    
    #actually run the build
    logfile = os.path.join(log_dir,sha,'build.txt')  
    rc = {}
    with open(logfile, "w") as f:
        rc['cli']     = call(str(cmd + ' --make_cli').split(),stdout=f,stderr=f)      
        rc['witness'] = call(str(cmd + ' --make_witness').split(),stdout=f,stderr=f)      
        rc['tests']   = call(cmd.split(),stdout=f,stderr=f)      

    #save build results
    raw_commit = commit.raw_data
    raw_commit.pop('files')
    state['commits'][sha] = {'rc':rc, 'commit':commit, 'tag':tag}
    if commit.commit.committer.date > state['last_commit_date']:
        state['last_commit_sha']  = sha    
        state['last_commit_date'] = commit.commit.committer.date
    save_state()

    print("return codes: %s" % (str(rc)))
    #If build is success run tests
    if(rc['tests'] == 0):
        run_tests(sha)
    
    #docker build
    if rc['cli'] == 0 and rc['witness'] == 0 :
        if tag or commit.commit.committer.date > state['docker_build_date']:
            #need to set sha and commit date as used by docker_push
            state['docker_build_sha']  = sha    
            state['docker_build_date'] = commit.commit.committer.date
            docker_build(tag)
        
    makeweb.make_web()
            
            
    
def check_github(repo):
    global state

    #Look for unbuilt tags
    #print ("Looking for new tags")
    tags = list(repo.get_tags())
    for t in tags:
        if t.name not in state['tags']:
            print("Found new tag, building: " + str(t.name))
            commit = repo.get_commit(t.commit.sha)
            build(commit, tag=t.name)
    
    #look for new commits
    #print("looking for new commits")
    commits = list(repo.get_commits( since=state['last_commit_date'] ))
    
    #go newest to oldest
    sorted_commits  = sorted(commits, key=lambda k: ( k.commit.committer.date, k.commit.author.date) , reverse=True)
    for c in sorted_commits: 
        if c.sha not in state['commits']:
            print("Found new commit, building: " + str(c.sha))
            print "%s : %s : %s" % (c.sha, c.commit.author.name, c.commit.committer.date)
            build(c)

    #check to see if it's been 24 hours last last docker_push
    docker_push(None)
    



def main():
    global state

    if os.path.isfile(state_file):
        with open(state_file,'rb') as f:
            state = pickle.load(f)
    else:
        #state = {'last_commit_date': datetime.datetime.now() - datetime.timedelta(hours = 96) }
        state = {}
        #commit from which build was fixed.
        state['last_commit_date'] = datetime.datetime(2015,8,8,0)
        state['tags'] = {}
        state['commits'] = {}
        state['docker_build_date'] = datetime.datetime(2015,8,1)
        state['docker_push_date'] = datetime.datetime(2015,8,1)

    #pop off a build to rebuild for testing
    #state['commits'].pop('dffd010e8a40fa08f25fd5c39c35248670031f33')
    #state['docker_push_date'] = datetime.datetime(2015,8,1)
    #state['last_commit_date'] = datetime.datetime(2015,8,8,0)
    

    #Setup github and read api key from file '~/github_api.key'
    with open (github_api_key_file, "r") as f:
        api_key = f.read().replace('\n','') 

    g = github.Github(api_key)
    repo = g.get_repo("cryptonomex/graphene")

    #loop forever, check every 5 minutes for changes
    while True:
       check_github(repo)
       sys.stdout.write('.')
       time.sleep(300)


if __name__ == "__main__":
    main()

