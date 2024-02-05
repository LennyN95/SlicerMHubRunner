import logging
import os
from typing import Annotated, Optional, List

import vtk, qt

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode
import DICOMSegmentationPlugin

#
# MRunner2
#

class MRunner2(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("MRunner2")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#MRunner2">module documentation</a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
""")

        # Additional initialization step after application startup is complete
        slicer.app.connect("startupCompleted()", registerSampleData)


#
# Register sample data sets in Sample Data module
#

def registerSampleData():
    """
    Add data sets to Sample Data module.
    """
    # It is always recommended to provide sample data for users to make it easy to try the module,
    # but if no sample data is available then this method (and associated startupCompeted signal connection) can be removed.

    import SampleData
    iconsPath = os.path.join(os.path.dirname(__file__), 'Resources/Icons')

    # To ensure that the source code repository remains small (can be downloaded and installed quickly)
    # it is recommended to store data sets that are larger than a few MB in a Github release.

    # MRunner21
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='MRunner2',
        sampleName='MRunner21',
        # Thumbnail should have size of approximately 260x280 pixels and stored in Resources/Icons folder.
        # It can be created by Screen Capture module, "Capture all views" option enabled, "Number of images" set to "Single".
        thumbnailFileName=os.path.join(iconsPath, 'MRunner21.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
        fileNames='MRunner21.nrrd',
        # Checksum to ensure file integrity. Can be computed by this command:
        #  import hashlib; print(hashlib.sha256(open(filename, "rb").read()).hexdigest())
        checksums='SHA256:998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95',
        # This node name will be used when the data set is loaded
        nodeNames='MRunner21'
    )

    # MRunner22
    SampleData.SampleDataLogic.registerCustomSampleDataSource(
        # Category and sample name displayed in Sample Data module
        category='MRunner2',
        sampleName='MRunner22',
        thumbnailFileName=os.path.join(iconsPath, 'MRunner22.png'),
        # Download URL and target file name
        uris="https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97",
        fileNames='MRunner22.nrrd',
        checksums='SHA256:1a64f3f422eb3d1c9b093d1a18da354b13bcf307907c66317e2463ee530b7a97',
        # This node name will be used when the data set is loaded
        nodeNames='MRunner22'
    )


#
# MRunner2ParameterNode
#

@parameterNodeWrapper
class MRunner2ParameterNode:
    """
    The parameters needed by module.

    inputVolume - The volume to threshold.
    imageThreshold - The value at which to threshold the input volume.
    invertThreshold - If true, will invert the threshold.
    thresholdedVolume - The output volume that will contain the thresholded volume.
    invertedVolume - The output volume that will contain the inverted thresholded volume.
    """
    inputVolume: vtkMRMLScalarVolumeNode
    imageThreshold: Annotated[float, WithinRange(-100, 500)] = 100
    invertThreshold: bool = False
    thresholdedVolume: vtkMRMLScalarVolumeNode
    invertedVolume: vtkMRMLScalarVolumeNode


#
# MRunner2Widget
#

class MRunner2Widget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/MRunner2.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = MRunner2Logic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.cmdTestHost.connect('clicked(bool)', self.onTestHostButton)
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

        # Dorpdowns (hosts)
        self.ui.hostSelector.addItems(self.logic.hosts)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self) -> None:
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if not self._parameterNode.inputVolume:
            firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
            if firstVolumeNode:
                self._parameterNode.inputVolume = firstVolumeNode

    def setParameterNode(self, inputParameterNode: Optional[MRunner2ParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if self._parameterNode and self._parameterNode.inputVolume:
            self.ui.applyButton.toolTip = _("Compute output volume")
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = _("Select input volume node")
            self.ui.applyButton.enabled = False

    def onTestHostButton(self) -> None:
        """
        Run processing when user clicks "Test Host" button.
        """
        
        # progressbar upgrade gradually for 10 seconds and stop when testSshHost returns either true or false
        self.ui.prgTestHost.setRange(0, 100)
        self.ui.prgTestHost.setValue(0)
        self.ui.prgTestHost.setFormat("Testing host: %p%")
        self.ui.prgTestHost.show()
        
        # try outsourced thread
        self.sshHelper = SSHHHelper(progressBar=self.ui.prgTestHost)
        self.sshHelper.run(hostid=self.ui.hostSelector.currentText)
    
        
        # with slicer.util.tryWithErrorDisplay(_("Failed to test host."), waitCursor=True):
        #     self.logic.testSshHost(self.ui.hostSelector.currentText)

    def onTestHostResult(self, isHostAvailable: bool) -> None:
        """
        Run processing when user clicks "Test Host" button.
        """
        self.ui.prgTestHost.hide()
        if isHostAvailable:
            slicer.util.confirmOkCancel("Host is available", "Host is available")
        else:
            slicer.util.confirmOkCancel("Host is not available", "Host is not available")

    def onApplyButton(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            
            # get node path from selected node
            input_image_node = self.ui.inputSelector.currentNode()
            input_image_paths = self.logic.get_node_paths(input_image_node)
            print(f"input_image_path: {input_image_paths}")
            
            # create temp dir
            
            # copy / upoad input image to temp dir
            
            # run processing on host
        
        # with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):

        #     # Compute output
        #     self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode(),
        #                        self.ui.imageThresholdSliderWidget.value, self.ui.invertOutputCheckBox.checked)

        #     # Compute inverted output (if needed)
        #     if self.ui.invertedOutputSelector.currentNode():
        #         # If additional output volume is selected then result with inverted threshold is written there
        #         self.logic.process(self.ui.inputSelector.currentNode(), self.ui.invertedOutputSelector.currentNode(),
        #                            self.ui.imageThresholdSliderWidget.value, not self.ui.invertOutputCheckBox.checked, showResult=False)

#
# Asynchronous class for ssh operations
#

class SSHHHelper:
    
    # run various asynchroneous tests and retrieve information from host
    # - test: host availability (except localhost)
    # - test: docker availability
    # - get:  docker version
    # - test: docker version (optional)
    # - get:  available mhub images (all starting with mhubai/... except base)
    
    timer: qt.QTimer
    progress: int = 0
    
    def __init__(self, progressBar):
        self.progressBar = progressBar
        
        # create qt timer
        self.timer = qt.QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.onTimeout)
        
    def onTimeout(self):
        # update progress
        self.progress += 10
        if self.progress >= 100:
            self.timer.stop()
        
        # cheak if thread stopped
        if not self.thread.is_alive():
            self.timer.stop()
            #self.progressBar.hide()
        
        # update ui
        self.progressBar.setValue(self.progress)
    
    def run(self, hostid: str):
        import threading

        # start timer
        self.timer.start()

        # create thread
        self.thread = threading.Thread(target=self.work, args=(hostid,))
        self.thread.start()
        

    def work(self, hostid: str):
        from sshconf import read_ssh_config
        from os.path import expanduser
        import paramiko
        
        # print
        print(f"Testing host: {hostid}", flush=True)
        
        # get host details
        c = read_ssh_config(expanduser("~/.ssh/config"))

        # assuming you have a host "svu"
        host = c.host(hostid)
        print("host details", host, flush=True)  # print the settings
        
        
        # instantiate ssh client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # try  to connect to host with ssh, outsource in non-blocking sub-thread:
        try:
            ssh.connect(
                hostname=host['hostname'],
                username=host['user'] if 'user' in host else None,
                port=host['port'] if 'port' in host else 22,
                key_filename=expanduser(host['identityfile']) if 'identityfile' in host else None,
                timeout=10
            )
            
            # check docker version and print results
            stdin, stdout, stderr = ssh.exec_command('docker --version')
            print(stdout.read().decode('utf-8'), flush=True)
            
            ssh.close()
        except Exception as e:
            print(f"Failed to connect to host: {hostid}: {e}", flush=True)

#
# MRunner2Logic
#

class MRunner2Logic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)
        self.setupPythonRequirements()
        hosts = self.getAvailableSshHosts()

    def getParameterNode(self):
        return MRunner2ParameterNode(super().getParameterNode())

    def setupPythonRequirements(self, upgrade=False):
        
        # install sshconf python package
        try:
          import sshconf
        except ModuleNotFoundError as e:
           #self.log('sshconf is required. Installing...')
           slicer.util.pip_install('sshconf')
        
        # install paramiko python package
        try:
            import paramiko
        except ModuleNotFoundError as e:
            #self.log('paramiko is required. Installing...')
            slicer.util.pip_install('paramiko')
        
    def getAvailableSshHosts(self) -> List[str]:
        from sshconf import read_ssh_config
        from os.path import expanduser

        c = read_ssh_config(expanduser("~/.ssh/config"))
        self.hosts = list(c.hosts())
        
    def get_node_paths(self, node) -> List[str]:
        storageNode=node.GetStorageNode()
        if storageNode is not None:
            return [storageNode.GetFullNameFromFileName()]
        else:
            instanceUIDs=node.GetAttribute('DICOM.instanceUIDs').split()
            return [slicer.dicomDatabase.fileForInstance(instanceUID) for instanceUID in instanceUIDs]




    def process(self,
                inputVolume: vtkMRMLScalarVolumeNode,
                outputVolume: vtkMRMLScalarVolumeNode,
                imageThreshold: float,
                invert: bool = False,
                showResult: bool = True) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """

        if not inputVolume or not outputVolume:
            raise ValueError("Input or output volume is invalid")

        import time
        startTime = time.time()
        logging.info('Processing started')

        # Compute the thresholded output volume using the "Threshold Scalar Volume" CLI module
        cliParams = {
            'InputVolume': inputVolume.GetID(),
            'OutputVolume': outputVolume.GetID(),
            'ThresholdValue': imageThreshold,
            'ThresholdType': 'Above' if invert else 'Below'
        }
        cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True, update_display=showResult)
        # We don't need the CLI module node anymore, remove it to not clutter the scene with it
        slicer.mrmlScene.RemoveNode(cliNode)

        stopTime = time.time()
        logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')

    def saveSegmentations(self, timestamp, database_type):
        
        # labelNodes = slicer.util.getNodes('*-label*')
        labelNodes = slicer.util.getNodesByClass('vtkMRMLSegmentationNode') 
        # slicer.mrmlScene.getNodesByClass("vtkMRMLSegmentationNode").UnRegister(None)
        nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLSegmentationNode')
        nodes.UnRegister(slicer.mrmlScene)
        
        logging.debug('All label nodes found: ' + str(labelNodes))
        savedMessage = 'Segmentations for the following series were saved:\n\n'
        
        import DICOMSegmentationPlugin
        exporter = DICOMSegmentationPlugin.DICOMSegmentationPluginClass()
        
        success = 0 
        
        db = slicer.dicomDatabase
        
        # for label in labelNodes.values():
        for label in labelNodes: 
        
            # labelName_ref = label.GetName()[:label.GetName().rfind("-")]
            # print('labelName_ref: ' + str(labelName_ref))
            # labelSeries = labelName_ref.split(' : ')[-1] # will be just the referenced SeriesInstanceUID 
            
            # Instead get the labelSeries = referencedSeriesInstanceUID, from the actual segmentation object DICOM metadata 
            # and not the name of the label 
            # volumeNode = label.GetNodeReference('referenceImageGeometryRef')
            labelSeries = self.refSeriesNumber 
            
            # For the SeriesDescription of the SEG object
            # labelName = "Segmentation for " + str(labelSeries)
            labelName = "Segmentation"
        
            # Create directory for where to save the output segmentations 
            segmentationsDir = os.path.join(db.databaseDirectory, self.selectedStudyName, labelSeries) 
            self.logic.createDirectory(segmentationsDir) 

            ### Get the referenced volume node without matching by name ### 
            referenceVolumeNode = label.GetNodeReference('referenceImageGeometryRef')
            
            shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
            
            # set these for now. 
            # study list could be from different patients. 
            patientItemID = shNode.CreateSubjectItem(shNode.GetSceneItemID(), self.selectedStudyName)
            studyItemID = shNode.CreateStudyItem(patientItemID, self.selectedStudyName)
            volumeShItemID = shNode.GetItemByDataNode(referenceVolumeNode) # set volume node 
            shNode.SetItemParent(volumeShItemID, studyItemID)
            segmentationShItem = shNode.GetItemByDataNode(label) # segmentation
            shNode.SetItemParent(segmentationShItem, studyItemID)
            
            
            if (database_type=="local"):
            
                # Export to DICOM
                exportables = exporter.examineForExport(segmentationShItem)
                for exp in exportables:
                    exp.directory = segmentationsDir
                    exp.setTag('SeriesDescription', labelName)
                    # exp.setTag('ContentCreatorName', username)
                # exporter.export(exportables)
                
                # uniqueID = username + '-' + "SEG" + '-' + timestamp 
                # labelFileName = os.path.join(segmentationsDir, uniqueID + ".dcm")
                
                labelFileName = os.path.join(segmentationsDir, 'subject_hierarchy_export.SEG'+exporter.currentDateTime+".dcm")
                print ('labelFileName: ' + str(labelFileName))
            
                # exporter.export(exportables, labelFileName)
                exporter.export(exportables)
            
            elif (database_type=="remote"):
            
                # Create temporary directory for saving the DICOM SEG file  
                downloadDirectory = os.path.join(slicer.dicomDatabase.databaseDirectory,'tmp')
                if not os.path.isdir(downloadDirectory):
                    os.mkdir(downloadDirectory)
                    
                # Export to DICOM
                exportables = exporter.examineForExport(segmentationShItem)
                for exp in exportables:
                    exp.directory = downloadDirectory
                    exp.setTag('SeriesDescription', labelName)
                    # exp.setTag('ContentCreatorName', username)
                
                labelFileName = os.path.join(downloadDirectory, 'subject_hierarchy_export.SEG'+exporter.currentDateTime+".dcm")
                print ('labelFileName: ' + str(labelFileName))
            
                exporter.export(exportables)
                
                # Upload to remote server 
                print('uploading seg dcm file to the remote server')
                self.copySegmentationsToRemoteDicomweb(labelFileName) # this one uses dicomweb client 
                
                # Now delete the files from the temporary directory 
                for f in os.listdir(downloadDirectory):
                    os.remove(os.path.join(downloadDirectory, f))
                # Delete the temporary directory 
                os.rmdir(downloadDirectory)
            
                # also remove from the dicom database - it was added automatically?
                
            success = 1 
        
            if success:
                # savedMessage = savedMessage + label.GetName() + '\n'
                savedMessage = savedMessage + labelName + '\n' # SeriesDescription of SEG
                logging.debug(label.GetName() + ' has been saved to ' + labelFileName)

        
        labelNodes = None
        nodes = None
        referenceVolumeNode = None
        
        return savedMessage

#
# MRunner2Test
#

class MRunner2Test(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        self.test_MRunner21()

    def test_MRunner21(self):
        """ Ideally you should have several levels of tests.  At the lowest level
        tests should exercise the functionality of the logic with different inputs
        (both valid and invalid).  At higher levels your tests should emulate the
        way the user would interact with your code and confirm that it still works
        the way you intended.
        One of the most important features of the tests is that it should alert other
        developers when their changes will have an impact on the behavior of your
        module.  For example, if a developer removes a feature that you depend on,
        your test should break so they know that the feature is needed.
        """

        self.delayDisplay("Starting the test")

        # Get/create input data

        import SampleData
        registerSampleData()
        inputVolume = SampleData.downloadSample('MRunner21')
        self.delayDisplay('Loaded test data set')

        inputScalarRange = inputVolume.GetImageData().GetScalarRange()
        self.assertEqual(inputScalarRange[0], 0)
        self.assertEqual(inputScalarRange[1], 695)

        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        threshold = 100

        # Test the module logic

        logic = MRunner2Logic()

        # Test algorithm with non-inverted threshold
        logic.process(inputVolume, outputVolume, threshold, True)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], threshold)

        # Test algorithm with inverted threshold
        logic.process(inputVolume, outputVolume, threshold, False)
        outputScalarRange = outputVolume.GetImageData().GetScalarRange()
        self.assertEqual(outputScalarRange[0], inputScalarRange[0])
        self.assertEqual(outputScalarRange[1], inputScalarRange[1])

        self.delayDisplay('Test passed')
