import sys, os, re 
from makeToolDockCategories import *
from xml.dom import minidom
from collections import Counter
from itertools import groupby

        
def findMode(lst):
    maxFreq =  max(map(lst.count, lst))
    modes = [i for i in lst if lst.count(i) == maxFreq]
    return modes
    
def reformatOWS(workflowName,inputFile,outputFile):
    doc = minidom.parse(inputFile)
    nodes = doc.getElementsByTagName("node")
    for node in nodes:
        node.attributes['project_name'].value=workflowName
        qname=node.getAttribute('qualified_name').split('.')[-1]
        node.attributes['qualified_name'].value=workflowName+'.'+qname+'.'+qname
    with open(outputFile,'w') as f:
        f.write(doc.toxml())

def changeNameInOWS(oldName,newName,filename):
    doc = minidom.parse(filename)
    nodes = doc.getElementsByTagName("node")
    for node in nodes:
        node.attributes['project_name'].value=newName
        qnameParts=node.getAttribute('qualified_name').split('.')
        if qnameParts[0] == oldName:
            qnameParts[0]=newName;
            node.attributes['qualified_name'].value='.'.join(qnameParts)
        node.attributes['project_name'].value=newName
     
def copyWorkflow(inputWorkflow,outputWorkflow):
    #to copy workflow copy all the files and then change the titles in the ows file
    #could use global regex but then we could run into troubles when the workflow names are part of other names
    os.system('cp -r inputWorkflow outputWorkflow')
    oldName=os.path.basename(os.path.normpath(inputWorkflow))
    newName=os.path.basename(os.path.normpath(outputWorkflow))
    if newName != oldName :
        oldOWS=outputWorkflow+'/'+oldName+'.ows'
        newOWS=outputWorkflow+'/'+newName+'.ows'
        os.system('mv oldOWS newOWS')
        changeNameInOWS(oldName,newName,newOWS)
        
def findWidgetPathFromLink(qualifiedName,groupName,basePath=''):
    parts=qualifiedName.split('.')
    link=basePath+'/biodepot/'+'/'.join(parts[0:-1])+'.py'
    widgetPath=os.path.dirname((os.readlink(link)))
   #check if absolute path
    if widgetPath[0]=='/':
        absWidgetPath=widgetPath
    else:
        absWidgetPath=os.path.abspath('{}/biodepot/{}/{}'.format(basePath,groupName,widgetPath))
    return absWidgetPath

        
def exportWorkflow (bwbOWS,outputWorkflow,basePath=""):
    #don't let it nuke the root directories 
    if not outputWorkflow.strip('/'):
        return
    os.system('rm -rf {}/widgets'.format(outputWorkflow))
    os.system('mkdir -p {}/widgets'.format(outputWorkflow))
    os.system('rm -rf {}/icon'.format(outputWorkflow))
    #first get all the widgetNames from the bwbOWS file generated by orange
    print(bwbOWS)
    doc = minidom.parse(bwbOWS)
    nodes = doc.getElementsByTagName("node")
    #find base workflowName
    if not nodes:
        return
    projectPaths=[]
    #copy widgets
    for node in nodes:
        projectPath=niceForm(node.getAttribute('project_name'),allowDash=False)
        widgetName=niceForm(node.getAttribute('name'),allowDash=False)
        projectPaths.append(projectPath)
        qname=node.getAttribute('qualified_name')
        widgetPath=findWidgetPathFromLink(qname,projectPath,basePath)
        #the link has
        os.system('mkdir -p {}/widgets/{}'.format(outputWorkflow,projectPath))
        os.system('cp -r {} {}/widgets/{}'.format(widgetPath,outputWorkflow,projectPath))
   
    #copy icons and info in setup.py for each projectPath
    for projectPath in list(set(projectPaths)):
        os.system('cp {}/biodepot/{}/__init__.py {}/widgets/{}/'.format(basePath,projectPath,outputWorkflow,projectPath))
        os.system('cp -r {}/biodepot/{}/icon {}/widgets/{}/'.format(basePath,projectPath,outputWorkflow,projectPath))

def importWorkflow(owsFile):
    changedSetup=False
    workflowDir=os.path.dirname(owsFile)
    doc = minidom.parse(owsFile)
    nodes = doc.getElementsByTagName("node")
    with open('/biodepot/setup.py','r') as f:
        setupData=f.read()
    projectList=re.findall(r'setup\(name="([^"]+)"',setupData)
    #find base workflowName
    if not nodes:
        return
    projectNames=[]
    #copy widgets
    for node in nodes:
        #differs from export in that we want to preserve the dashes in the names for changing setup.py later
        projectName=niceForm(node.getAttribute('project_name'),allowDash=True)
        widgetName=niceForm(node.getAttribute('name'),allowDash=False)
        projectNames.append(projectName)
        projectPath=niceForm(projectName,allowDash=False)
        qname=node.getAttribute('qualified_name')
        parts=qname.split('.')
        destLink='/biodepot/'+'/'.join(parts[0:-1])+'.py'
        pythonFile='{}/widgets/{}/{}/{}.py'.format(workflowDir,projectPath,widgetName,widgetName)
        print ('mkdir -p /biodepot/{}'.format(projectPath))
        print ('ln -sf {} {}'.format(pythonFile,destLink))
        os.system('mkdir -p /biodepot/{}'.format(projectPath))
        os.system('ln -sf {} {}'.format(pythonFile,destLink))
    #update the entryname in the setup.py directory

    for projectName in list(set(projectNames)):
        projectPath=niceForm(projectName,allowDash=False)
        os.system('rm -rf /biodepot/{}/icon'.format(projectPath))
        os.system('cp -r {}/widgets/{}/icon  /biodepot/{} '.format(workflowDir,projectPath,projectPath))
        os.system('cp  {}/widgets/{}/__init__.py  /biodepot/{}/.'.format(workflowDir,projectPath,projectPath))
        if projectName not in  projectList:
            setupData+=entryString(projectName,projectPath)
            changedSetup=True
    
    if changedSetup:
        with open('/biodepot/setup.py','w') as f:
            f.write(setupData)
        os.system('cd /biodepot && pip install -e .')


