FROM centos:7
MAINTAINER "Alex Corvin" <acorvin@redhat.com>

RUN yum -y install epel-release && yum clean all

RUN yum -y install git python2-setuptools \
    sshpass libffi-devel gcc python-devel \
    openssl-devel make nss_wrapper && yum clean all

RUN curl -o /tmp/get-pip.py https://bootstrap.pypa.io/get-pip.py \
    && python /tmp/get-pip.py && /bin/rm /tmp/get-pip.py
RUN pip install --upgrade pip && pip install --upgrade setuptools

COPY . /cvengine
RUN cd /cvengine && python setup.py install

# Ensure that the root group has write access in $HOME
# This is necessary because, when running a container in
# Openshift, a random UID will be assigned at runtime. This
# UID will not have a valid username, but will be a member
# of the root group
RUN chgrp -Rf root $HOME && chmod -Rf g+w $HOME

CMD ["/cvengine/run_container_validation"]
