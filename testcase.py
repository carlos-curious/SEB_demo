#!/usr/local/bin/python2.7
#coding: UTF-8
import unittest, time
import testcommon
import xmlrunner
import requests
from xml.etree import ElementTree
import datetime
import sys,os

notificationPort=8086
globalReceipt=-1

class sebdemoMoTestSuite(testcommon.sebdemoTestCase):

	def setUp(self):
		global globalReceipt
		self.config=testcommon.sebdemoTestCaseConfig()
		self.config.useSelenium=False
		self.config.connectToDB=True

		if testcommon.suite.baseURL=="":
                        # sebdemourl.com is an alias defined in docker-compose.yml for haproxy
                        # tz/sebdemo/incoming.php is proxy to apps:8088 (sebdemomo) by the haproxy
                        testcommon.suite.baseURL="https://sebdemourl.com:443/tz/sebdemo/incoming.php"
		self.sebdemoUrl=testcommon.suite.baseURL
		self.closedPaybillUrl="https://sebdemourl.com:443/tz/sebdemo/"
		self.msisdn="255472744454"
		self.timestamp=time.strftime('%Y/%m/%d %H:%M:%S %z')
                                
		self.service="ALAN DIGITAL LTD"
		self.reference="800123"
		self.channel="TANZANIA.sebdemo"
		self.amount="100"
		self.transactionType = "CUSTOMER_PAYBILL"
		self.headers = {'Content-Type':'application/xml'}
		self.successMessage="SUCCESS"
		self.failureMessage="FAILURE"

		super(sebdemoMoTestSuite, self).setUp()

		if globalReceipt==-1:
			maxId=self.getMaxIdFromDatabase()
				if maxId!=-1:
					globalReceipt=maxId
				else:
					globalReceipt="1000000000"
                

	"""
	Test to send successful lodgement request
	"""

	def testSuccessfulLodgement(self):
		global globalReceipt

    	globalReceipt=str(int(globalReceipt)+1)
		print globalReceipt
		transTimestamp = int(time.time())
            
    	self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
    	xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
    	result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
		time.sleep(1)

    	xml_response = str(result.text)
    	status_code = result.status_code
    	self.assertEquals(status_code,200)
    	self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt, self.successMessage), "Unexpected response received")

		self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
		self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")

	"""
	Test to send dubplicate lodgement request
	"""

	def testDuplicateLodgement(self):
	    global globalReceipt                
	    globalReceipt=str(int(globalReceipt)+1)
	    print globalReceipt
	    transTimestamp = int(time.time())
	    
	    self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")                
	    xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
	    result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
	    time.sleep(1)

	    xml_response = str(result.text)
	    status_code = result.status_code
	    self.assertEquals(status_code,200)
	    self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt, self.successMessage))

		self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
		self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")

		xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
		result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
		time.sleep(1)

		xml_response = str(result.text)
		status_code = result.status_code
		self.assertEquals(status_code,200)
		self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt, self.successMessage))

		self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"More than one e-money transaction has been created")
		self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "More that one lodgement found in archive table")

	
	"""
	Test to send lodgement on closed paybill request
	"""
	def testClosedPaybill(self):
		global globalReceipt

        globalReceipt=str(int(globalReceipt)+1)
        print globalReceipt
        transTimestamp = int(time.time())

		self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

		xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
		result = self.makesebdemoMoRequest(self.closedPaybillUrl, xml, self.headers)
		time.sleep(1)

		xml_response = str(result.text)
		status_code = result.status_code
		self.assertEquals(status_code,200)
		self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))

		self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction has been created")
		self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")



    """
    Test to send lodgement with a malformed request
    """
    def testMalformedRequest(self):
		global globalReceipt

        globalReceipt=str(int(globalReceipt)+1)
        print globalReceipt
        transTimestamp = int(time.time())

        self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

        xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
        # <transaction1> is ok but <1transaction> an error and not present is also fine?!?
        malformedXml=xml.replace("<transaction>","<tran1saction>")
        result = self.makesebdemoMoRequest(self.sebdemoUrl, malformedXml, self.headers)
        time.sleep(1)

        xml_response = str(result.text)
        status_code = result.status_code

        self.assertEquals(status_code,200)
        self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt, self.successMessage), "Unexpected response received")

        self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
        self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")


    """
    Test to send lodgement with invalid receipt request
    Tola accept any receipt (including "") so no such invalid receipt will occur
    An empty receipt will get a success response from tola and the transaction will be created in the database
    """
    def testInvalidTimestamp(self):
            global globalReceipt

            #Empty timestamp
            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())
            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
            
            xml = self.formatXML("", self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")


            #Timestamp outside validity window (past)
            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())
            oldTimestamp = time.strftime('%Y/%m/%d %H:%M:%S %z',time.localtime(int(time.time())-200000))
            print "%s" % oldTimestamp

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
            
            xml = self.formatXML(oldTimestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))


            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")


            #Timestamp outside validity window (future)
            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())
            oldTimestamp = time.strftime('%Y/%m/%d %H:%M:%S %z',time.localtime(int(time.time())+150000))
            print "%s" % oldTimestamp

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
            
            xml = self.formatXML(oldTimestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))


            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")


            #Timestamp inside validity window
            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())
            oldTimestamp = time.strftime('%Y/%m/%d %H:%M:%S %z',time.localtime(int(time.time())-150000))
            print "%s" % oldTimestamp

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
            
            xml = self.formatXML(oldTimestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt, self.successMessage), "Unexpected response received")

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")           

    """
    Test to send lodgement with invalid receipt request
    Tola accept any receipt (including "") so no such invalid receipt will occur
    An empty receipt will get a success response from tola and the transaction will be created in the database
    """
    def testInvalidReceipt(self):
            global globalReceipt

            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")
	
            xml = self.formatXML(self.timestamp, self.service, self.reference, "", self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
			self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")


    """
    Test to send lodgement with invalid service request
    An empty service request will get a success response from tola and but the transaction will not be created
    """
    def testInvalidService(self):
            global globalReceipt

            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

            xml = self.formatXML(self.timestamp, "",self.reference, globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
	time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt,self.successMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")

    """
    Test to send lodgement with invalid reference request
    An empty service request will get a success response from tola and but the transaction will not be created
    """
    def testInvalidReference(self):
            global globalReceipt

            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

            xml = self.formatXML(self.timestamp, self.service, "", globalReceipt, self.amount, self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt,self.successMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")


    """
    Test to send lodgement with invalid amount request
    An empty amount request will get a fail response from tola and the transaction will not be created
    """
    def testInvalidAmount(self):
            global globalReceipt

            #Amount too small (100 is the minimum)
            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

            xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, "50", self.msisdn, self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")


    """
    Test to send lodgement with invalid msisdn request
    An empty msisdn request will get a fail response from tola and the transaction will not be created
    """
    def testInvalidMsisdn(self):
            global globalReceipt

            globalReceipt=str(int(globalReceipt)+1)
            print globalReceipt
            transTimestamp = int(time.time())

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

            xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, "-1", self.transactionType)
            result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
            time.sleep(1)

            xml_response = str(result.text)
            status_code = result.status_code
            self.assertEquals(status_code,200)
            self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><result>%s</result></response>" % (self.failureMessage))

            self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0,"E-money transaction has been created")
            self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),0, "Lodgement transactions found in archive table")

	"""
	Test to send lodgement with invalid transaction type request
	An empty service request will get a success response from tola and but the transaction will not be created        
	"""
	def testInvalidTransactionType(self):
	        global globalReceipt

	        globalReceipt=str(int(globalReceipt)+1)
	        print globalReceipt
	        transTimestamp = int(time.time())

	        self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 0, "E-money transaction already exists")

	        xml = self.formatXML(self.timestamp, self.service, self.reference, globalReceipt, self.amount, self.msisdn,"")
	        result = self.makesebdemoMoRequest(self.sebdemoUrl, xml, self.headers)
	        time.sleep(1)

	        xml_response = str(result.text)
	        status_code = result.status_code
	        self.assertEquals(status_code,200)
			self.assertEquals(xml_response, "<xml version=\"1.0\" encoding=\"UTF-8\"> <response><receipt>%s</receipt><result>%s</result></response>" % (globalReceipt,self.successMessage))

	        # weird log behaviour TBI
	        self.assertTrue(self.getTransactionCountFromDatabase(globalReceipt) == 1,"No e-money transaction has been created")
	        self.assertEquals(len(self.getArchivedTransactionsAfter("lodge",transTimestamp)),1, "No lodgement found in archive table")


	def getTransactionCountFromDatabase(self, transactionReference):
	        cur = self.db.cursor()
	        sql="select id from database.table where tableid='" + transactionReference + "' and channel='" + self.channel + "'"
	        print sql
	        cur.execute(sql)
	        result=cur.fetchall()
	        return len(result)

	def getMaxIdFromDatabase(self):
	        cur = self.db.cursor()
	        sql="select max(tableid) from database.table where channel='" + self.channel + "'"
	        print sql
	        cur.execute(sql)
	        result=cur.fetchall()
	        if  result[0]['max(tableid)']!=None:
	                return result[0]['max(tableid)']
	        else:
	                return -1


	def formatXML(self, timestamp, service, reference, receipt, amount, msisdn, transactionType):
			xml = """<?xml version="1.0" encoding="utf-8"?>
		 		<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
					xmlns:xsd="http://www.w3.org/2001/XMLSchema"
					xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
				<soap:Body>
					<transaction>
						<timestamp>%s</timestamp>
								...
					</transaction>
				</soap:Body>
			</soap:Envelope>""" % (timestamp, service, reference, receipt, amount, msisdn, transactionType)

		return xml

	def makesebdemoMoRequest(self, url, xml, headers):
		response = requests.post(url=url, data=xml, cert='/etc/ssl/sebdemo.com/ssl_haproxy_20150729', headers=headers)
		return response

	def tearDown(self):
		super(sebdemoMoTestSuite, self).tearDown()

if __name__ == '__main__':

        with testcommon.ThreadedHTTPServer(('', notificationPort), testcommon.DummyNotificationHTTPHandler) as notificationListenServer:
	       testcommon.suite.run(sebdemoMoTestSuite)
