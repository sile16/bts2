#!/usr/bin/python

import sys
import os
from subprocess import call


path = '/build/graphene'

def usage():

    print ("")
    print ("Usage: docker run -v <local path for build>:/build <image> [commit sha or tag]")
    print ("        will build latest head version unless tag or sha is specified")
    print ("")
    print ("Example: docker run -v /root:/build sile16/graphene-build:pre testnet")
    print ('Result:  graphene tag "testnet" will be cloned and built into /root/graphene')
    exit(1)


def main():

    print 'Number of arguments:', len(sys.argv), 'arguments.'
    print 'Argument List:', str(sys.argv) 
    sys.stdout.flush()

    if len(sys.argv) > 2:
         print ("too many arguments")
         usage()

    if not os.path.isdir('/build'):
        print("No build volume mounted, please us docker -v <local volume>:/build to mount a build directory to image")
        usage()

    os.chdir('/build')
   

    sha = None
    if len(sys.argv) == 2:
        sha = sys.argv[1]
        if sha == "--help":
            usage()

    if not os.path.isdir(path):
        #Path doesn't exist, lets clone graphene into there
        call( '/usr/bin/git clone https://github.com/cryptonomex/graphene.git'.split() )
        os.chdir(path)
        call('/usr/bin/git submodule update --init --recursive'.split())        
    else:
        #Path does exist
        #todo: check that it's a valid, git repo and pointing to cryptonomex/graphene with git remote -v
        os.chdir(path)


    rt=0
    if(sha):
        #checkout a specific sha or tag
        rt += call(['/usr/bin/git','fetch', '--recurse-submodules'])
        rt += call(['/usr/bin/git','checkout',sys.argv[1]] )
        rt += call(['/usr/bin/git','submodule','update','--recursive'])
    else:
        #update to latest head version of master
        rt = call( '/usr/bin/git pull --recurse-submodules origin master'.split())
    
    if rt != 0 :
        print ("Error updating repo")
        usage()
        
    rc = call( '/usr/bin/cmake -DBOOST_ROOT="/usr/local/" -DCMAKE_BUILD_TYPE=Debug -DENABLE_COVERAGE_TESTING=true -DBUILD_TESTS=true .'.split() )
    #rc = call( ['/usr/bin/cmake','.'] )

    if rc != 0:
        print("cmake failed, exiting build")
        usage()

    exit( call( ['/usr/bin/make','-j4'] ) )

if __name__ == "__main__":
    main()
