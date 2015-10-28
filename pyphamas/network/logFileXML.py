import xml.etree.ElementTree as ET
import xml.dom.minidom as DOM
import traceback
def testXML():
    root = ET.Element('root')
    root.text = str('\n')
    oldFile = ET.parse('bfWeights.log')
    root.append(oldFile.getroot())
    tree = ET.ElementTree(root)
    tree.write('TESTING.log')
    return

def testDOM():
    impl = DOM.getDOMImplementation()
    docNode = impl.createDocument(None, 'DocNode', None)
    root = docNode.documentElement
    root.setAttribute('root', 'rootNode')
    thisElem = docNode.createElement('childNode')
    thisElem.setAttribute('Child', 'ChildNode')
    root.appendChild(thisElem)
    f = open('TESTING.log', 'w')
    f.write(docNode.toprettyxml())
    f.close
    return

def testFileAppend():
    impl = DOM.getDOMImplementation()
    docNode = impl.createDocument(None, 'DocNode', None)
    node = DOM.parse('./TESTING.log')
    root = docNode.documentElement
    root.setAttribute('root', 'newRoot')
    thisElem = node.firstChild.cloneNode(True)
    thisElem = docNode.importNode(thisElem, True)
    root.appendChild(thisElem)

    RemoveText(root)

    f = open('TESTING.log','w')
    f.write(docNode.toprettyxml())
    f.close()


def RemoveText(theNode):

    if theNode.hasChildNodes():
        RemoveText(theNode.firstChild);

    sibling = theNode.nextSibling;

    if (theNode.nodeType == DOM.Element.TEXT_NODE):
        if theNode.parentNode.tagName != 'Beamformer_weights':
            theNode.parentNode.removeChild(theNode);

    if sibling is not None:
        RemoveText(sibling);

def newRTIClogFile(fileName, outFileName, coeIdx, outIdx):
    impl = DOM.getDOMImplementation()
    nodes = [];

    for f in fileName:
        try:
            logFileName = f+'.log'
#            print 'newRTICLogFile: '+f
            nodes.append(DOM.parse(logFileName))
        except IOError:
            traceback.print_exc()
            return -1   

    docNode = impl.createDocument(None, 'beamformer', None)
    root = docNode.documentElement

    for k in range(len(nodes)):
        thisElem = nodes[k].firstChild.cloneNode(True)
        thisElem = docNode.importNode(thisElem, True)
        thisElem.tagName = 'BF_{0}_Weights'.format(str(k+1))
        outputIdx = docNode.createElement('output_idx_for_these_weights')
        outputIdx.setAttribute('Index_start', str(outIdx))
        thisElem.appendChild(outputIdx)
        root.appendChild(thisElem)
        
    RemoveText(root)
    with open(outFileName+'.log', 'w') as f:
        f.write(docNode.toprettyxml('','','utf-8'))

def bigLogFile(inFileList,outFileName):
    '''
    inFileList > list of input logfiles from each BF weight set
    outFileName > outputFile name with NO extension (.log is added)
    '''
#be sure to test if log files exist. if not, skip this
    impl = DOM.getDOMImplementation()
    nodes = [];

    for file in inFileList:
        try:
            nodes.append(DOM.parse(file))
        except IOError:
            traceback.print_exc()
            return -1   

    docNode = impl.createDocument(None, 'beamformer', None)
    root = docNode.documentElement

    for k in range(len(nodes)):
        thisElem = nodes[k].firstChild.cloneNode(True)
        thisElem = docNode.importNode(thisElem, True)
        thisElem.tagName = 'BF_{0}_Weights'.format(str(k+1))
        root.appendChild(thisElem)

    RemoveText(root)

    f = open(outFileName+'.log','w')
    f.write(docNode.toprettyxml('','','utf-8'))
    f.close()
#########################################################################
def testSkipNoFile(inFileList, outFileName):
    
    impl = DOM.getDOMImplementation()
   #nodes = [];

    docNode = impl.createDocument(None, 'beamformer', None)
    root = docNode.documentElement

    for (k, file) in enumerate(inFileList):
        try:
            node = DOM.parse(file)
            thisElem = node.firstChild.cloneNode(True)
            thisElem = docNode.importNode(thisElem, True)
            thisElem.tagName = 'BF_{0}_Weights'.format(str(k+1))
            root.appendChild(thisElem)
        except IOError:
            thisElem = docNode.createElement('BF_{0}_Weights'.format(str(k+1)))
            subElem = docNode.createElement('Beamformer_weights')
            subElem.setAttribute('filename', 'UNKNOWN. LOG FILE DOES NOT EXIST FOR \''+str(file)+'\'')
            thisElem.appendChild(subElem)
            root.appendChild(thisElem)
            #traceback.print_exc()

    RemoveText(root)

    f = open(outFileName+'.log','w')
    f.write(docNode.toprettyxml())
    f.close()
    
    return outFileName+'.log'
'''


%These log files have NO text nodes, but the xmlread adds some emptys in :(
RemoveText(docRootNode)

xmlFileName = ['All_Beamformer_Weights', '.log'];
xmlwrite(xmlFileName, docNode);
end


function [] = RemoveText(theNode)

TEXT_NODE = 3;

if theNode.hasChildNodes
    RemoveText(theNode.getFirstChild());
end

sibling = theNode.getNextSibling;

if (theNode.getNodeType()== TEXT_NODE)
    theNode.getParentNode().removeChild(theNode);
end

if ~isempty(sibling)
    RemoveText(sibling);
end

end
'''
