FROM ubuntu:14.04

# Update, Install Prerequisite Packages and cleanup
RUN apt-get update && apt-get -y install \
  git libreadline-dev uuid-dev g++ libdb++-dev libdb-dev zip \
  libssl-dev openssl build-essential python-dev autotools-dev libicu-dev \
  libbz2-dev automake doxygen cmake ncurses-dev libtool nodejs nodejs-legacy npm mc \
  autoconf wget lcov \
  && apt-get -y autoremove && rm -rf /var/lib/apt/lists/*

# Install Boost 1.57 and cleanup
WORKDIR /tmp
RUN wget -c 'http://sourceforge.net/projects/boost/files/boost/1.57.0/boost_1_57_0.tar.bz2/download' && \
  tar -xf download && \
  cd /tmp/boost_1_57_0 && \
  ./bootstrap.sh --prefix=/usr/local/ && \
  ./b2 install && \
  cd / && \
  rm -rf /tmp/boost_1_57_0 && \
  rm -f /tmp/download

WORKDIR /
ADD build.py /
ENTRYPOINT ["/usr/bin/python", "/build.py" ]
