#!/usr/bin/python
import argparse
import subprocess
import curses
from curses.textpad import Textbox, rectangle
from docker import Client
import sys
import os
import time

class SEBdemoDocker:
	def __init__(self):

		parser = argparse.ArgumentParser(description='Command line arguments')

		parser.add_argument("operation",
			help='the operation required',
			choices=[
				'menu',
				'destroy',
				'new',
				'shell',
				'dbshell',
				'loadsql',
				'reloadsql',
				'cmd',
				'make',
				'rmake',
				'nodestart',
				'nodestop',
				'runptest',
				'rungtest',
				'startnodes',
				'stopnodes',
				'status'
			])

		self.operations = {
			"menu":self.menu,
			"destroy":self.destroy,
			"new":self.new,
			"shell":self.shell,
			"dbshell":self.dbshell,
			"loadsql":self.loadsql,
			"reloadsql": self.reloadsql,
			"cmd":self.cmd,
			"make":self.make,
			"rmake":self.rmake,
			"nodestop":self.nodeStop,
			"nodestart":self.nodeStart,
			"runptest":self.runPTest,
			"rungtest":self.runGTest,
			"startnodes":self.startNodes,
			"stopnodes":self.stopNodes,
			"status":self.status
		}

		parser.add_argument("extra1",
			nargs='?',
			default='',
			help='extra argument 1')
		parser.add_argument("extra2",
			nargs='?',
			default='',
			help='extra argument 1')
		parser.add_argument("extra3",
			nargs='?',
			default='',
			help='extra argument 1')

		parser.add_argument('-p', '--project', help='set the project name', default='docker')
		parser.add_argument('-i', '--ipstatic', action='store_true', help='set the static ip from file docker-compose.staticip.yml')

		self.args = parser.parse_args()

		# needs to be <container name>_<instance> from docker_compose
		self.appsContainer=self.args.project+"_apps_1"
		self.webContainer=self.args.project+"_web_1"
		self.livedbContainer=self.args.project+"_livedb_1"
		self.archivedbContainer=self.args.project+"_archivedb_1"
		self.pythontestContainer=self.args.project+"_pythontest_1"

		self.dockerRepositories = []
		self.dockerRepositories.append("SEBdemoapps64c6")
		self.dockerRepositories.append("pythontest")

		self.devfiles = "/SEBdemo/base"

	def performOperation(self,operation=""):
		if operation == "":
			operation = self.args.operation
		func = self.operations.get(operation)
		return func()

	def menu(self):
		self.performOperation(self.operations.keys()[buildMenu(self.operations.keys(),"Main")])

	def up(self):
		if (self.args.ipstatic):
			print("Set statis IPs from file 'docker-compose.staticip.yml'")
			self.ipparam="-f docker-compose.yml -f docker-compose.staticip.yml"
		else:
			print("Use dynamic IPs")
			self.ipparam=""

		print("bringing up "+self.args.project)
		subprocess.call("docker-compose "+self.ipparam+" --project-name "+self.args.project+" up -d",  shell=True)

	def down(self):
		print("bringing down "+self.args.project)
		subprocess.call("docker-compose --project-name "+self.args.project+" down", shell=True)

	def checkRepositories(self):
		for repository in self.dockerRepositories:
			print("checking repository: %s" % repository)
			subprocess.call("docker pull dockerregistry.ie.oxygen8.com:5000/%s" % repository, shell=True)

	def build(self):
		self.checkRepositories()
		print("building "+self.args.project)
		subprocess.call("docker-compose --project-name "+self.args.project+" build", shell=True)

	def destroy(self):
		print("destroying "+self.args.project)
		self.down()
		subprocess.call("docker-compose --project-name "+self.args.project+" rm", shell=True)

	def new(self):
		print("initialising new stack "+self.args.project)
		self.destroy()
		self.build()
		self.setPermissions()
		self.up()
		print("copy deployments.inc.php to web tree")
		self.runCommand(self.webContainer,"cp /SEBdemo/scripts/deployment.inc.php /SEBdemo/base/web/common/.")
		self.makeAll() # could thread this and the sql load for a perf gain but might be confusing
		self.loadsql() # also this gives time for sql to start properly before we start injecting sql
		self.runCommand(self.appsContainer,"/etc/init.d/sendmail restart")
		self.startNodes()

	def setPermissions(self):
		print("setting logs directory writable")
		subprocess.call("chmod 777 workarea/logs", shell=True)
		print("setting smarty writable")
		subprocess.call("chmod 777 base/web/smarty/new/english", shell=True)

		# frontend stuff
		subprocess.call("mkdir -p base/o8testcommon/frontend/app/cache/volt", shell=True)
		print("setting volt cache directory writable")
		subprocess.call("chmod -R 777 base/o8testcommon/frontend/app/cache", shell=True)
		print("setting frontend log directory writable")
		subprocess.call("chmod -R 777 base/o8testcommon/frontend/app/log", shell=True)

	def loadsql(self):
		print("loading sql "+self.args.project+" from "+self.livedbContainer)

		if self.runCommand(self.livedbContainer,"bash /database/initdb") != 0:
			print "Error populating livedb, exiting"
			sys.exit(-1)

		if self.runCommand(self.archivedbContainer,"bash /database/initarchivedb") !=0:
			print "Error populating archivedb, exiting"
			sys.exit(-1)

		if self.args.extra1 !="":
			self.runCommand(self.livedbContainer,"bash /database/runsql /SEBdemo/base/src/test/python/data/"+self.args.extra1+".sql")

		print("loaded sql ")

	def reloadsql(self):
		self.loadsql()
		self.stopNodes()
		self.startNodes()

	def shell(self):
		container = self.appsContainer
		if self.args.extra1:
			# verify valid container here?
			container = self.args.project+"_"+self.args.extra1
		print("Opening shell: 	"+container)
		subprocess.call("docker exec -ti "+container+" bash", shell=True)

	def dbshell(self):
		container = self.livedbContainer
		if self.args.extra1:
			# verify db container here?
			container = self.args.project+"_"+self.args.extra1
		print("Opening mysql shell: 	"+self.livedbContainer)
		subprocess.call("docker exec -ti "+container+" mysql", shell=True)

	def status(self):
		subprocess.call("docker-compose  --project-name "+self.args.project +" ps ", shell=True)

	def cmd(self):
		print("args2 %s" % self.args.extra2)
		if self.args.extra2 !="":
				container=self.args.extra2
		else:
				container=self.appsContainer
		print("running command: "+self.args.extra1+" in container "+ container)
		self.runCommand(container,self.args.extra1)

	def make(self):
		if self.args.extra1 == "all":
			self.makeAll()
			return

		if self.args.extra1 == "clean":
			self.makeClean()
			return

		if self.args.extra1 == "test":
			self.makeTest()
			return

		print("making: "+self.args.extra1)
		self.runCommand(self.appsContainer,"make -s -C "+self.devfiles+"/src bin/"+self.args.extra1)

	def makeClean(self):
		print("cleaning...")
		self.runCommand(self.appsContainer,"make -s -C "+self.devfiles+"/src clean")

	def startNodes(self):
		print("attempting to start nodes")
		self.runCommand(self.appsContainer,self.devfiles+"/o8testcommon/commandnodes.py start")

	def stopNodes(self):
		print("stopping nodes...")
		self.runCommand(self.appsContainer,self.devfiles+"/o8testcommon/commandnodes.py stop")

	def reMakeAll(self):
		print("performing full make")
		self.stopNodes()
		self.makeAll()
		print("build complete")
		self.startNodes()

	def makeAll(self):
		print("cleaning...")
		self.runCommand(self.appsContainer,"make -s -C "+self.devfiles+"/src clean")
		print("building...")
		self.runCommand(self.appsContainer,"make -s -C "+self.devfiles+"/src all")
		self.makeTest()

	def makeTest(self):
		print("building test...")
		self.runCommand(self.appsContainer,"make -s -C "+self.devfiles+"/src TEST")

	def nodeStart(self):
		print("starting: "+self.args.extra1)
		self.runCommand(self.appsContainer,self.devfiles+"/o8testcommon/commandnodes.py start %s"%self.args.extra1)

	def nodeStop(self):
		print("stopping: "+self.args.extra1)
		self.runCommand(self.appsContainer,self.devfiles+"/o8testcommon/commandnodes.py stop %s"%self.args.extra1)

	def rmake(self):
		if self.args.extra1 == "all":
			self.reMakeAll()
			return

		print("remaking: "+self.args.extra1)
		self.nodeStop()
		self.make()
		self.nodeStart()

	def runPTest(self):
		if self.args.extra1 == "all" or self.args.extra1 == "list":
			tests = (self.runCommand(self.appsContainer, "ls -1 -A1 "+self.devfiles+"/src/test/python/",False)).splitlines()
			for test in tests:
				base,ext=os.path.splitext(test)
				if ext==".py":
					if self.args.extra1 == "list":
						print test.replace(".py","")
					else:
						self.args.extra1=base
						print self.args.extra1 + " " + self.args.extra2
						self.reloadsql()
						time.sleep(1)
						print("running: %s" % self.devfiles+"/src/test/python/"+self.args.extra1)
						self.runCommand(self.pythontestContainer,self.devfiles+"/src/test/python/"+self.args.extra1+".py "+self.args.extra2)
									
		else:
			self.reloadsql()
			time.sleep(1)
			print("running: %s" % self.devfiles+"/src/test/python/"+self.args.extra1)
			if self.runCommand(self.pythontestContainer,self.devfiles+"/src/test/python/"+self.args.extra1+".py "+self.args.extra2) !=0:
				print "Error running test suite, exiting"
				sys.exit(-1)

	def runGTest(self):
		if self.args.extra1 == "all":
			print "Running all gtests"
			self.runCommand(self.appsContainer,'python ' + self.devfiles+'/src/test/gtest/runall.py')
		elif self.args.extra1 == "list":
			print "Listing all gtest available"
			tests=self.runCommand(self.appsContainer, "ls -1 -A1 "+self.devfiles+"/src/test/gtest/bin",False).splitlines()
			for test in tests:
				if not test.startswith("."):
					print test
		else:
			print("Running gtest: "+self.args.extra1)
			self.runCommand(self.appsContainer,self.devfiles+'/src/test/gtest/bin/' +self.args.extra1 )

	def runCommand(self,container,cmd, stream=True):
		cli = Client(base_url='unix://var/run/docker.sock')
		ex = cli.exec_create(container=container, cmd=cmd)
		if stream:
			for result in cli.exec_start(exec_id=ex["Id"],stream=True):
				print(result)
			return cli.exec_inspect(exec_id=ex["Id"])['ExitCode']
		else:
			return cli.exec_start(exec_id=ex["Id"])
			


def buildMenu(options, title):
	screen = curses.initscr()

	screen.clear()
	screen.border(0)
	screen.addstr(1, 3, title)
	screen.addstr(2, 3, "Select an option:")

	startOptions = 3
	nOption = 1

	for option in options:
		screen.addstr(startOptions+nOption, 4, "%d - %s" % (nOption,option))
		nOption+=1

	screen.refresh()
	curses.echo()
	input = screen.getstr(2, 24, 2)

	curses.endwin()

	return (int(input)-1)

if __name__ == '__main__':
	interface = SEBdemoDocker()
	interface.performOperation()
