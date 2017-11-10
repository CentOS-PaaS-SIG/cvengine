FROM centos:7
MAINTAINER "Alex Corvin" <acorvin@redhat.com>

RUN yum -y install git python2-setuptools python-pip \
    sshpass libffi-devel gcc python-devel \
    openssl-devel make && yum clean all

RUN curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py \
    && python /tmp/get-pip.py && /bin/rm /tmp/get-pip.py
RUN pip install --upgrade pip && pip install --upgrade setuptools

COPY . $WORKDIR/cvengine
RUN cd $WORKDIR/cvengine && python setup.py install

CMD ["cvengine"]
