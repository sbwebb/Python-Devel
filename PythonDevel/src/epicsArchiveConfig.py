'''
Created on Dec 19, 2013

Parses an EPICS database file, looking for the 'info' fields that have the 'archive' parameter,
and buildes an XML file containing the archive information.

Call this program like so: $ python epicsArchiveConfig.py <database name>.db

@author: Brad Webb <webbsb@ornl.gov>
'''

__version__ = '1.0.1'

import sys
import re

import xml.etree.ElementTree as etree
from xml.etree.ElementTree import ElementTree, Element



class EpicsRecord(object):
    '''
    This class represents an EPICS record and its list of attributes,
    e.g., field, info.
    '''
    
    def __init__(self, rec_type, rec_name):
        '''
        Initialize the the EPICS record instance. Give it a
        name, type, and append attributes, e.g., field, info...
        
        @param rec_type: Stores the type of the EPICS record
        @param rec_name: Stores the name of the EPICS record
        '''
        self.rec_type = rec_type
        self.rec_name = rec_name
        self.rec_attributes = []
        
    def get_record_name(self):
        '''
        @return: The name of the EPICS record
        '''
        return self.rec_name
    
    def get_record_type(self):
        '''
        @return: The type of the EPICS record
        '''
        
        return self.rec_type
    
    def to_string(self):
        '''
        @return: The a string representing the EPICS record
        '''
        return self.rec_type + " " + self.rec_name
    
    def add_attribute(self, attribute):
        '''
        @param attribute: Is an object of type EpicsRecordAttributes
        '''
        self.rec_attributes.append(attribute)
        
    def get_attributes(self):
        '''
        @return: A list of EpicsRecordAttributes
        '''
        return self.rec_attributes
    


class EpicsRecordAttributes(object):
    '''
    This class represents an attribute belonging to an EPICS record,
    e.g., field(DESC, "Some description") 
    '''

    def __init__(self, attr_type, attr_name, attr_value):
        '''
        Initialize,
        
        @param attr_type: Type of the attribute belonging to the record: field or info
        @param attr_name: Name given to the attribute: DESC, INP, OUT, SCAN ...
        @param attr_value: The value of the attribute: (DESC, "My description"); (INP, "@PLC ..."); (OUT, "@PLC ..."); (SCAN, "Passive")
        '''
        
        self.attr_type = attr_type
        self.attr_name = attr_name
        self.attr_value = attr_value
        
    def get_attribute_type(self):
        '''
        @return: A string representing the attribute type: field or info 
        '''
        return self.attr_type
    
    def get_attribute_name(self):
        '''
        @return: A string representing the attribute name: DESC, INP, OUT, SCAN ...
        '''
        return self.attr_name
    
    def get_attribute_value(self):
        '''
        @return: A string representing the attribute value: DESC, "My description"
        '''
        return self.attr_value
    
    def to_string(self):
        '''
        @return: A string representing the whole EPICS attribute
        '''
        return self.attr_type + " " + self.attr_name + " " + "\"" + self.attr_value + "\""


 
class ArchiveAttribute(EpicsRecordAttributes):
    '''
    This class represents an 'archive' attribute belonging to an EPICS record,
    e.g., info(archive, "monitor, 00:00:05")
    '''

    def __init__(self, attr_type, attr_name, attr_value):
        EpicsRecordAttributes.__init__(self, attr_type, attr_name, attr_value) 
        '''
        Initialize,
        
        @param attr_type: Type of the attribute belonging to the record: info
        @param attr_name: Name given to the attribute: archive
        @param attr_value: The value of the attribute: "SCAN, 00:00:04, HIHI LOLO HIGH LOW"
        '''
        
        self.mode = None
        self.period = None
        self.properties = None
        
        '''
        What? Python doesn't support modifier spans? (?i) (?-i)
        '''
        ARCHPATTERN = re.compile('\s*(?P<mode>[mM][oO][nN][iI][tT][oO][rR]|[sS][cC][aA][nN])\s*,\s*(?P<period>[0-5][0-9]:[0-5][0-9]:[0-5][0-9])\s*,?\s*(?P<rec_props>.*)?')

        '''
        Match object. Should match this format: info(archive, "<sample mode>, <sample period>, [list of properties...]")
        TODO: Throw something if the pattern is not matched.
        '''
        m = ARCHPATTERN.match(attr_value)
        
        if m:
            '''
            mode and period are mandatory
            '''
            if m.group(1) and m.group(2):
                self.mode = m.group(1)
                self.period = m.group(2)
                '''
                EPICS record properties (VAL, RVAL etc.) are optional.
                '''
                if m.group(3):
                    self.properties = m.group(3).split()
            else:
                print "ERROR! ArchiveAttribute: Not enough parameters."
        else:
            print "ERROR! ArchiveAttribute: Invalid info field."

    def to_string(self):
        '''
        @return: A string representing the whole EPICS archive attribute
        '''
        st = "ArchiveAttribute.to_string: " + self.mode + " " + self.period
        if self.properties is not None:
            for p in self.properties:
                st += ' ' + p
        return st

    def get_sample_mode(self):
        '''
        @return: A string representing the sample mode of the archive attribute
        '''
        return self.mode
    
    def get_sample_period(self):
        '''
        @return: A string representing the sample period of the archive attribute 
        formatted as: HH:MM:SS
        '''
        return self.period

    def get_sample_properties_length(self):
        '''
        @return: Length of the attribute properties list
        '''
        if self.properties is not None:
            return len(self.properties)
        else:
            return 0

    def get_sample_properties(self):
        '''
        @return: A list containing the attribute properties,
        e.g., ["HIHI", "LOLO", "HIGH", "LOW"]
        '''
        return self.properties


RECORD_SIGNATURE = re.compile('\s*record\s*\((?P<r_type>.*),\s*"?(?P<r_name>.*?)"?\s*\)')
ATTRIBUTE_SIGNATURE = re.compile('\s*(?P<attr_type>(field|info))\s*\(\s*(?P<attr_name>.*),\s*"(?P<attr_value>.*?)"\s*\)')

print "System Args: length(", len(sys.argv), ") ", str(sys.argv)

if len(sys.argv) < 2:
    print 'Missing input file name!'
    sys.exit(2)
    
inputFilename = sys.argv[1]
outputFilename = str(sys.argv[1]).rstrip('.db') + "_arch.xml"

recList = []
eRecord = None


'''
Parse the file, line by line.
'''
try:
    f = open(sys.argv[1], 'r')
    print f
    
    for line in f:
    
        '''
        Look for an EPICS record, identified by:
    
        record(<type>, <record name>) {    #Signature
        fields(...)                #Fields
        ...
        }
        '''
        m = RECORD_SIGNATURE.match(line)
    
        if m:
            eRecord = EpicsRecord(m.group('r_type'), m.group('r_name'))
            
            '''
            Now see if the signature line has the opening brace "{"
            at the end. If not, it may be on the next line by itself. 
            '''
            while not re.search('\{', line):
                line = f.next()
                
            while not re.search('\}', line):
                line = f.next()
                m = ATTRIBUTE_SIGNATURE.match(line)
                if m:
                    if m.group('attr_type') == 'field':
                        attrib = EpicsRecordAttributes(m.group("attr_type"), m.group("attr_name"), m.group("attr_value"))
                        eRecord.add_attribute(attrib)
                    elif m.group('attr_type') == 'info' and m.group('attr_name') == 'archive':
                        attrib = ArchiveAttribute(m.group("attr_type"), m.group("attr_name"), m.group("attr_value"))
                        eRecord.add_attribute(attrib)
                            
            recList.append(eRecord)
            
except Exception, argument:
    print 'Some error happened...', argument    
    f.close()
    sys.exit(2)
    
        
'''
Now build XML file

<engineconfig>
6      <group>
7        <name>Detectors</name>
8          <channel><name>BL7:Det:East:All:StatDebounce</name><period>00:01:00</period><monitor/></channel>
9          <channel><name>BL7:Det:West:All:StatDebounce</name><period>00:01:00</period><monitor/></channel>
10      </group>
11      <group>
12        <name>Environment</name>
13          <channel><name>CF_BmLn:TT07108:T</name><period>00:10:00</period><scan/></channel>
14      </group>
15      <group>
16        <name>Motors</name>
17          <channel><name>BL7:Mot:Parker:HROT.RBV</name><period>00:00:10</period><monitor>0.5</monitor></channel>
18          <channel><name>BL7:Sample:Omega.RBV</name><period>00:00:10</period><monitor/></channel>
19          <channel><name>BL7:Sample:X.RBV</name><period>00:00:10</period><monitor/></channel>
20          <channel><name>BL7:Sample:Y.RBV</name><period>00:00:10</period><monitor/></channel>
21          <channel><name>BL7:Sample:Z1.RBV</name><period>00:00:10</period><monitor/></channel>
22      </group>
23    </engineconfig>
'''

root = Element('engineconfig')
group = Element('group')
group_name = Element('name')
group_name.text = 'Default_Group'
group.append(group_name)

#Build Group Channels...
for rec in recList:
    for attr in rec.get_attributes():
        if attr.get_attribute_type() == 'info':
            if attr.get_sample_properties() is None:
                channel = Element('channel')
                channel_name = Element('name')
                channel_name.text = rec.get_record_name()
                channel.append(channel_name)
                
                channel_period = Element('period')
                channel_period.text = attr.get_sample_period()
                channel.append(channel_period)
                
                channel_mode = Element(attr.get_sample_mode().lower())
                channel.append(channel_mode)
                
                group.append(channel)
            else:
                for prop in attr.get_sample_properties():
                    channel = Element('channel')
                    channel_name = Element('name')
                    channel_name.text = rec.get_record_name() + '.' + prop
                    channel.append(channel_name)
                
                    channel_period = Element('period')
                    channel_period.text = attr.get_sample_period()
                    channel.append(channel_period)
                
                    channel_mode = Element(attr.get_sample_mode().lower())
                    channel.append(channel_mode)
                
                    group.append(channel)
root.append(group)



def indent(elem, level=0):
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

'''
Write XML to file.
'''
indent(root)
etree.dump(root)
tree = ElementTree(root)
try:
    tree.write(open(outputFilename, 'w'), None, None, None, None)
except Exception, argument:
    print 'Some error happened...', argument    
    f.close()
    sys.exit(2)












