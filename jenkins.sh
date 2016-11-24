PATH=/usr/local/sbin:/usr/local/bin:$PATH

which docker-compose

DIR=`pwd`
cd $DIR/o8testcommon
git checkout master
cd $DIR/o8common
git checkout master
cd $DIR/docker

./sebdemo -p jenkins new
./sebdemo -p jenkins status

./sebdemo -p jenkins make test

./sebdemo -p jenkins  rungtest all

./sebdemo -p jenkins  runptest all "-v 0 -o /xnet/results"

./debdemo -p jenkins destroy
