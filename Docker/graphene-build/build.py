#!/usr/bin/python

import sys
import os
import subprocess
from subprocess import call
import argparse


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

    parser.add_argument('--build_type', choices=['Debug','Release'],default='Debug', help='Change build type')
    parser.add_argument('--devshares', action='store_true', help='build from devshares instead of graphene')

    #I decided to only program in specific make targets becuase I didn't like the idea of a command line param
    #being accepted and then used in a call function from a security point of view.  Not sure how this will be
    #potentially used up stream...
    parser.add_argument('--make_all', dest='make_args', action='append_const', const='all', help='specify make target of all (Default targets defined by the Makefile)')
    parser.add_argument('--make_tests', dest='make_args', action='append_const', const='all_tests', help='only build tests and other targets specified')
    parser.add_argument('--make_cli_wallet', dest='make_args', action='append_const', const='cli_wallet', help='only build wallet and other targets specified')
    parser.add_argument('--make_witness', dest='make_args', action='append_const', const='witness_node', help='only build witness and other targets specified')

    args = parser.parse_args()

    if not os.path.isdir(local_path):
        print("No build volume mounted, please us docker -v <local volume>:/build to mount a build directory to image")
        usage(parser)

    if args.devshares:
        path = os.path.join(local_path,'devshares')
        git_url = git_devshares
    
    if (not os.path.isdir(path)) or os.listdir(path) == [] :
        #Path doesn't exist, or it does but it's empty lets clone graphene into there
        os.chdir(local_path)
        call( ['/usr/bin/git','clone',git_url] )
    
    else:
        #Path does exist and has files
        #lets make sure it's a git repo and points to the correct remote repo
        os.chdir(path)
        try:
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
    call( '/usr/bin/git submodule update --init --recursive'.split())


    rt=0
    if(args.sha):
        #checkout a specific sha or tag
        rt += call(['/usr/bin/git','fetch', '--recurse-submodules'])
        rt += call(['/usr/bin/git','checkout',args.sha] )
        rt += call(['/usr/bin/git','submodule','update','--recursive'])
    else:
        #update to latest head version of master
        rt += call( '/usr/bin/git pull --recurse-submodules origin master'.split())
        #rt += call( '/usr/bin/git submodule update --init --recursive'.split())
        #rt += call( '/usr/bin/git pull --recurse-submodules origin master'.split())
            
    if rt != 0 :
        print ("Error updating repo")
        usage(parser)
    
    
    cmd = '/usr/bin/cmake -DBOOST_ROOT="/usr/local/" -DCMAKE_BUILD_TYPE=%s  .' % (args.build_type)

    print(cmd.split())
    rc = call(cmd.split())

    if rc != 0:
        print("cmake failed, exiting build")
        usage(parser)

    cmd = ['/usr/bin/make','-j4']

    if args.make_args:
        cmd += args.make_args

    print(cmd)
    exit( call(cmd) )

if __name__ == "__main__":
    main()
