#!/usr/bin/python

import sys
import os
import subprocess
from subprocess import call
import argparse
import re


def usage(parser):

    parser.print_help()
    #make sure messages get pushed to console
    sys.stdout.flush()
    exit(1)


def main():
    
    local_path = '/build'
    path = os.path.join(local_path,'graphene')

    git_graphene = 'https://github.com/cryptonomex/graphene.git'
    git_devshares = 'https://github.com/bitshares/devshares.git'
    git_url = git_graphene  #set graphene as default git_url

    description = '''    The script will build graphene to a specific commit or tag

    Example: docker run -v /home/john:/build sile16/graphene-build 
    Result:  latest graphene will be built into /home/john/graphene '''


    parser = argparse.ArgumentParser(prog='docker run -v <local path for build>:/build sile16/graphene-build',
                                     description=description, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('sha', type=str, nargs='?' ,help='Commit sha or master branch tag')

    parser.add_argument('--build-type' , choices=['Debug','Release'],default='Debug', help='Change build type')
    parser.add_argument('--devshares', action='store_true', help='build from devshares instead of graphene')
    parser.add_argument('--branch', '-b', type=str, default='master', help='specify a specific branch to build from')

    #I decided to only program in specific make targets becuase I didn't like the idea of a command line param
    #being accepted and then used in a call function from a security point of view.  Not sure how this will be
    #potentially used up stream...
    parser.add_argument('--make-target', '-t' , dest='make_args', choices=['cli_wallet','witness_node','all'], help='only build specified target (default is all)')
    parser.add_argument('--make-jobs', '-j', dest='make_jobs', type=int ,help='make: Allow N jobs at once; infinite jobs with no arg')

    args = parser.parse_args()
    #print(args)
    #exit(1)

    if not os.path.isdir(local_path):
        print("No build volume mounted, please us docker -v <local volume>:/build to mount a build directory to image")
        usage(parser)

    if args.devshares:
        path = os.path.join(local_path,'devshares')
        git_url = git_devshares
    
    if args.branch:
        regex = re.compile('^[a-zA-Z0-9\-_\./]+$')
        if not regex.match(args.branch):
            print("Invalid branch name: {}".format(args.branch))
            usage(parser)
          

    if (not os.path.isdir(path)) or os.listdir(path) == [] :
        #Path doesn't exist, or it does but it's empty lets clone graphene into there
        os.chdir(local_path)
        cmd = "/usr/bin/git clone {}".format(git_url)
        if args.branch:
            cmd += " -b {}".format(args.branch)
        print("running {}".format(cmd))
        call( cmd.split() )
    
    else:
        #Path does exist and has files
        #lets make sure it's a git repo and points to the correct remote repo
        os.chdir(path)
        try:
            print("running ['/usr/bin/git','remote','-v']")
            out = subprocess.check_output(['/usr/bin/git','remote','-v'])
        except subprocess.CalledProcessError as gitexec:
            #git returned an error code, not a valid git repo
            print "Git Error, point the build to an empty folder or one with a valid git repo"
            print "Git error: ", gitexec.returncode, gitexec.output
            usage(parser) 

        if git_url not in out:    
            print "Error: directory points to a different git repo"
            print "Git Error, point the build to an empty folder or one with a valid git repo"
            print "expected repo:",git_url
            print "git remote -v:",out
            usage(parser)
        

    #update all submodules    
    os.chdir(path)
    print("running: /usr/bin/git submodule update --init --recursive")
    call( '/usr/bin/git submodule update --init --recursive'.split())


    rt=0
    if(args.sha):
        #checkout a specific sha or tag
        cmd = '/usr/bin/git fetch --recurse-submodules'
        print("running {}".format(cmd))
        rt += call(cmd.split())
        cmd = '/usr/bin/git checkout {}'.format(args.sha)
        if args.branch:
            cmd += ' -b {}'.format(args.branch)
        print("running {}".format(cmd))
        rt += call(cmd.split())
        cmd = '/usr/bin/git submodule update --recursive'
        print("running {}".format(cmd))
        rt += call(cmd.split())
    else:
        #update to latest head version of branch
        cmd = '/usr/bin/git pull --recurse-submodules origin {}'.format(args.branch)
        print("running {}".format(cmd))
        rt += call( cmd.split())
        #rt += call( '/usr/bin/git submodule update --init --recursive'.split())
        #rt += call( '/usr/bin/git pull --recurse-submodules origin master'.split())
            
    if rt != 0 :
        print ("Error updating repo, try deleting build folder and retry")
        usage(parser)
    
    
    cmd = '/usr/bin/cmake -DBOOST_ROOT="/usr/local/" -DCMAKE_BUILD_TYPE=%s  .' % (args.build_type)

    print(cmd.split())
    rc = call(cmd.split())

    if rc != 0:
        print("cmake failed, exiting build")
        usage(parser)


    cmd = ['/usr/bin/make']

    if args.make_jobs:
        cmd += ['-j',str(args.make_jobs)]

    if args.make_args:
        cmd += [args.make_args]

    print(cmd)
    exit( call(cmd) )

if __name__ == "__main__":
    main()
