import logging
import os
from typing import Annotated, Any, Optional, List, Callable, Literal, Dict
from dataclasses import dataclass

import slicer, ctk, vtk, qt
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

import hashlib
from datetime import datetime

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
        self.ui.cmdKillObservedProcesses.connect('clicked(bool)', self.onKillObservedProcessesButton)

        # Dorpdowns (hosts)
        self.ui.hostSelector.addItems(["localhost"] + self.logic.hosts)
        self.ui.hostSelector.connect('currentIndexChanged(int)', self.onHostSelect)

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

    def onKillObservedProcessesButton(self) -> None:
        """
        Run processing when user clicks "Kill Observed Processes" button.
        """
        
        # kill all observed processes
        for task in ProgressObserver._tasks:
            task.kill()

    def onHostSelect(self, index: int) -> None:
        assert self.logic is not None
        
        # update host information
        self.updateHostInfo()
        
        # get selected host id
        hostid = self.ui.hostSelector.currentText
        
        # if host is not yet tested, test it
        if hostid not in self.logic.hostInfo:
            self.initiateHostTest()
           
    def updateHostInfo(self) -> None:
        assert self.logic is not None
        
        # get selected host id
        hostid = self.ui.hostSelector.currentText
        
        # get host information
        hinfo = self.logic.hostInfo[hostid] if hostid in self.logic.hostInfo else None
        
        # update can connect status
        if hinfo is None:
            self.ui.lblHostConnectionStatus.setText("N/A")
        elif hinfo.canConnect:
            self.ui.lblHostConnectionStatus.setText("OK")
        else:
            self.ui.lblHostConnectionStatus.setText("Failed")
            
        # update docker version
        if hinfo is None:
            self.ui.lblHostDockerVersion.setText("N/A")
        else:
            self.ui.lblHostDockerVersion.setText(hinfo.dockerVersion)
        
        # update gpus list
        self.ui.lstHostGpu.clear()
        if hinfo is not None:
            for gpu in hinfo.gpus:
                if gpu == "": continue
                item = qt.QListWidgetItem()
                item.setFlags(item.flags() | qt.Qt.ItemIsUserCheckable)
                item.setCheckState(qt.Qt.Unchecked)
                item.setText(gpu)
                self.ui.lstHostGpu.addItem(item) 

    def initiateHostTest(self) -> None:
        assert self.logic is not None
        
        def onStart():
            self.ui.lblHostTestStatus.setText("Testing.")
            self.ui.hostSelector.enabled = False
            self.ui.cmdTestHost.enabled = False
        
        def onProgress(progress: int):
            self.ui.lblHostTestStatus.setText(f"Testing ({progress}s)")
        
        def onStop():
            self.ui.hostSelector.enabled = True
            self.ui.cmdTestHost.enabled = True
            self.ui.lblHostTestStatus.setText("Done.")

            # update host information
            self.updateHostInfo()
            
        self.logic.testSshHost(self.ui.hostSelector.currentText, onStart, onProgress, onStop)

    def onTestHostButton(self) -> None:
        """
        Run processing when user clicks "Test Host" button.
        """
            
        self.initiateHostTest()
    
    def onApplyButton(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        
        ##### TEST (works)
        # assert self.logic is not None
        # local_dir = "/Users/lenny/Projects/SlicerMHubIntegration/SlicerMHubRunner/return_data"
        # dsegfiles = self.logic.scanDirectoryForFilesWithExtension(local_dir)
        # self.logic.addFilesToDatabase(dsegfiles, operation="copy")
        # self.logic.importSegmentations(dsegfiles)
        # return
    
        ###### TEST (works)
        # # print all selected gpus from self.ui.lstHostGpu
        # for i in range(self.ui.lstHostGpu.count):
        #     item = self.ui.lstHostGpu.item(i)
        #     if item.checkState() == qt.Qt.Checked:
        #         print(item.text())
        # return
        
        ###### TEST (for caching on host)
        # get InstanceUIDs (only available for nodes loaded through the dicom module)
        node = self.ui.inputSelector.currentNode()
        instanceUIDs = node.GetAttribute('DICOM.instanceUIDs')

        # create hash from instanceUIDs
        hash = hashlib.sha256()
        hash.update(instanceUIDs.encode('utf-8'))
        instance_idh = hash.hexdigest()

        print(instance_idh)
    
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            assert self.logic is not None
            
            host_base = "/tmp/mhub_slicer_extension"
            host_dir = os.path.join(host_base, instance_idh)
            local_dir = "/Users/lenny/Projects/SlicerMHubIntegration/SlicerMHubRunner/return_data"
            local_in_zip = os.path.join(local_dir, "input.zip")
            local_out_dir = os.path.join(local_dir, "output")
            
            if not os.path.isdir(local_dir):
                os.makedirs(local_dir)
                
            if not os.path.isdir(local_out_dir):
                os.makedirs(local_out_dir)
            
            # get selected gpus
            # TODO: make gpus None 
            gpus = []
            for i in range(self.ui.lstHostGpu.count):
                item = self.ui.lstHostGpu.item(i)
                if item.checkState() == qt.Qt.Checked:
                    print("Selected GPU: ", item.text())
                    gpus.append(i)
            
            #
            # self.logic.zip_node(
            #     self.ui.inputSelector.currentNode(),
            #     local_in_zip
            # )
            
            #
            self.logic.run_mhub(
                applyButton=self.ui.applyButton,
                hostid=self.ui.hostSelector.currentText,
                model="gc_lunglobes",
                gpus=gpus,
                host_dir=host_dir,
                local_dir=local_dir,
                local_in_zip=local_in_zip,
                local_out_dir=local_out_dir
            )
        
            #
            dsegfiles = self.logic.scanDirectoryForFilesWithExtension(local_dir)
            self.logic.addFilesToDatabase(dsegfiles, operation="copy")
            self.logic.importSegmentations(dsegfiles)
        
#
# Asynchronous class for ssh operations
#

class AsyncTask:
    
    timer: qt.QTimer
    timeout: int = 20           # seconds
    progress: int = 0           # seconds
    
    def __init__(self):        
        # create qt timer
        self.timer = qt.QTimer()
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.onTimeout)
        
    def onTimeout(self):
        # update progress
        self.progress += 1
        if self.progress >= self.timeout * 10:
            self.onStop()
            self.timer.stop()
        
        # cheak if thread stopped
        if not self.thread.is_alive():
            self.onStop()
            self.timer.stop()
            
        # call onProgress
        self.onProgress(int(self.progress / 10))
        
    def start(self):
        self.beforeStart()
        self.timer.start()
        self.thread.start()
        #self.work(*self.work_args, **self.work_kwargs)
        self.onStart()
        
    def setup(self, *args, **kwargs):
        import threading
        self.work_args = args
        self.work_kwargs = kwargs
        self.thread = threading.Thread(target=self.work, args=args, kwargs=kwargs, daemon=False)

    def beforeStart(self):
        pass

    def onStart(self):
        pass
    
    def onProgress(self, progress: int):
        pass

    def work(self):
        pass
    
    def onStop(self):
        pass

@dataclass
class HostInformation:
    name: str
    canConnect: bool
    testedOn: datetime
    
    dockerVersion: str
    gpus: List[str]
    cachedSubjects: List[str]

class SSHHHelper(AsyncTask):
    
    # run various asynchroneous tests and retrieve information from host
    # - test: host availability (except localhost)
    # - test: docker availability
    # - get:  docker version
    # - test: docker version (optional)
    # - get:  available mhub images (all starting with mhubai/... except base)
    
    timeout: int = 100           # seconds
    
    # status variables (set from worker thread and read from main thread)
    messages: List[str] = []
    canConnect: bool = False
    dockerVersion: str = "N/A"
    gpus: List[str] = []
    cache: List[str] = []
    
    # callbacks
    _onStart: Optional[Callable[[], None]] = None
    _onProgress: Optional[Callable[[int], None]] = None
    _onStop: Optional[Callable[[HostInformation], None]] = None
    
    def setup(self, hostid: str):
        super().setup(hostid=hostid)
        self.hostid = hostid
       
    def setOnStart(self, callback: Callable[[], None]):
        self._onStart = callback
        
    def setOnProgress(self, callback: Callable[[int], None]):
        self._onProgress = callback
        
    def setOnStop(self, callback: Callable[[HostInformation], None]):
        self._onStop = callback
       
    def onStart(self):
        # invoke callback if defined
        if self._onStart:
            self._onStart()
       
    def onProgress(self, progress: int):
        # invoke callback if defined
        if self._onProgress:
            self._onProgress(progress)
       
    def onStop(self):
       
        # compile host information
        hostInfo = HostInformation(
            name=self.hostid,
            canConnect=self.canConnect,
            testedOn=datetime.now(),
            dockerVersion=self.dockerVersion,
            gpus=self.gpus,
            cachedSubjects=self.cache
        )
        
        # invoke callback if defined
        if self._onStop:
            self._onStop(hostInfo)
       
    def work(self, hostid: str):
        import subprocess
        
        # try connection
        if hostid == "localhost":
            self.canConnect = True
        else:
            try:
                subprocess.run(["ssh", hostid, "exit"], timeout=5, check=True)
                self.canConnect = True
            except Exception as e:
                self.canConnect = False
                self.messages.append(f"Failed to connect to host: {hostid}: {e}")
                
        # get docker version
        if hostid == "localhost":
            try:
                result = subprocess.run(["docker", "--version"], timeout=5, check=True, capture_output=True)
                self.dockerVersion = result.stdout.decode('utf-8')
            except Exception as e:
                self.dockerVersion = "E"
                self.messages.append(f"Failed to get docker version: {e}")  
        elif self.canConnect:        
            try:
                result = subprocess.run(["ssh", hostid, "docker --version"], timeout=5, check=True, capture_output=True)
                self.dockerVersion = result.stdout.decode('utf-8')
            except Exception as e:
                self.dockerVersion = "E"
                self.messages.append(f"Failed to get docker version: {e}")

        # get gpus list
        if hostid == "localhost":
            try:
                result = subprocess.run(["nvidia-smi", "--list-gpus"], timeout=5, check=True, capture_output=True)
                self.gpus = result.stdout.decode('utf-8').split("\n")
            except Exception as e:
                self.gpus = []
                self.messages.append(f"Failed to get gpus: {e}")
        elif self.canConnect:        
            try:
                result = subprocess.run(["ssh", hostid, "nvidia-smi", "--list-gpus"], timeout=5, check=True, capture_output=True)
                self.gpus = result.stdout.decode('utf-8').split("\n")
            except Exception as e:
                self.gpus = []
                self.messages.append(f"Failed to get gpus: {e}")

        # check cached subjects (directory names in /tmp/mhub_slicer_extension)
        host_base = "/tmp/mhub_slicer_extension"
        if hostid == "localhost": 
            self.cache = os.listdir(host_base)
        elif self.canConnect:
            try: 
                result = subprocess.run(["ssh", hostid, f"ls {host_base}"], timeout=5, check=True, capture_output=True)
                self.cache = result.stdout.decode('utf-8').split("\n")
            except Exception as e:
                self.cache = []
                self.messages.append(f"Failed to get cache: {e}")

class ProgressObserver:
    
    # # variables
    # _timeout: int = 0
    # _timer: qt.QTimer
    # _proc = None
    
    # # callbacks
    # _onProgress: Optional[Callable[[int], None]] = None
    # _onStop: Optional[Callable[[bool], None]] = None
    
    # keep track of all running tasks
    _tasks: List['ProgressObserver'] = []
    
    def __init__(self, cmd: List[str], frequency: float = 2, timeout: int = 0):
        """
        cmd:       command to execute in subprocess
        frequency: progress update frequency in Hz
        timeout:   timeout in seconds, 0 means no timeout
        """
        
        # set variables
        self._timeout = timeout
        self._frequency = frequency
        self._seconds_elapsed = 0.0
        
        self._proc = None
        self._onProgress: Optional[Callable[[float], None]] = None
        self._onStop: Optional[Callable[[bool, int], None]] = None
        
        # initialize timer
        self._timer: qt.QTimer = qt.QTimer()
        self._timer.setInterval(1000/frequency)
        self._timer.timeout.connect(self._onTimeout)
        
        # run command
        self._run(cmd)
        
        # add to tasks
        self._tasks.append(self)
        
    def _run(self, cmd: List[str]):
        import subprocess
        
        self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._timer.start()

    def _onTimeout(self):
        assert self._proc is not None
        
        # update time
        self._seconds_elapsed += 1.0 / self._frequency
        
        # check timeout condition
        if self._timeout > 0 and self._seconds_elapsed > self._timeout:
            self._timer.stop()
            self._proc.kill()
            
            # invoke callback if defined
            if self._onStop:
                self._onStop(True, -1)
        
        # stop timer if process is done
        if self._proc.poll() is not None:
            returncode = self._proc.returncode
            self._timer.stop()

            # invoke callback if defined
            if self._onStop:
                self._onStop(False, returncode)
                
            return

        # call progress method
        if self._onProgress:
            # self._proc.stdout.read().decode('utf-8') # <--- carful, can block, only when needed and do experiment
            self._onProgress(self._seconds_elapsed)

    def onStop(self, callback: Callable[[bool, int], None]):
        self._onStop = callback
        
    def onProgress(self, callback: Callable[[float], None]):
        self._onProgress = callback

    def kill(self):
        self._timer.stop()
        if self._proc is not None:
            self._proc.kill()
        self._tasks.remove(self)
  
class ProcessChain:
    
    @dataclass
    class CMD:
        index: int
        cmd: List[str]
        name: Optional[str] = None
        frequency: float = 2
        timeout: int = 0
        returncode: Optional[int] = None
        success: Optional[bool] = None
        started: bool = False
    
    def __init__(self):
        self.cmds: List['ProcessChain.CMD'] = []
        self.started = False
        self.stopped = False
        self.success = True
        self.index = -1
        
        self._seconds_elapsed = 0.0
        
        self._onStop: Optional[Callable[[bool], None]] = None
        self._onProgress: Optional[Callable[['ProcessChain.CMD', int], None]] = None
        
    def add(self, cmd: List[str], name: Optional[str] = None, timeout: int = 0, frequency: float = 2):
        assert not self.started, "Process chain already started"
        self.cmds.append(self.CMD(len(self.cmds), cmd, name, frequency, timeout))
        
    def start(self):
        self.started = True

        # start first process
        self._start_next()
        
    def _start_next(self):
        if self.index < len(self.cmds):
            self.index += 1
            self._start_process(self.cmds[self.index].cmd)
        else:
            self.stopped = True            

            # invoke callback if defined
            if self._onStop:
                self._onStop(True)
       
    def _on_process_stop(self, timeout, returncode):
        if timeout or returncode != 0:
            self.success = False
            self.stopped = True
            
            # invoke callback if defined
            if self._onStop:
                self._onStop(False)
        else:
            self._start_next()
        
    def _on_process_progress(self, time):
        self._seconds_elapsed += time
        
        # invoke progress callback if defined
        if self._onProgress:
            self._onProgress(self.cmds[self.index], time)
        
    def _start_process(self, cmd: List[str]):
        p = ProgressObserver(cmd)
        p.onStop(self._on_process_stop)
        p.onProgress(self._on_process_progress)
    
    def onStop(self, callback: Callable[[bool], None]):
        self._onStop = callback

    def onProgress(self, callback: Callable[['ProcessChain.CMD', int], None]):
        self._onProgress = callback


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
        self.hosts: List[str] = []
        self.hostInfo: Dict[str, HostInformation] = {}

        # load available hosts
        self.getAvailableSshHosts()

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
        
    def testSshHost(self, hostid: str, onStart: Callable[[], None], onProgress: Callable[[int], None], onStop: Callable[[], None]):
        # instantiate and setup the async task
        sshHelper = SSHHHelper()
        sshHelper.setup(hostid=hostid)
        
        # custom callbacks
        def _onStop(hostInfo: HostInformation):
            self.hostInfo[hostid] = hostInfo
            onStop()
        
        # assign callbacks
        sshHelper.setOnStart(onStart)
        sshHelper.setOnProgress(onProgress)
        sshHelper.setOnStop(_onStop)

        # start the helper async task
        sshHelper.start()
        
        
    def get_node_paths(self, node) -> List[str]:
        storageNode=node.GetStorageNode()
        if storageNode is not None:
            return [storageNode.GetFullNameFromFileName()]
        else:
            instanceUIDs=node.GetAttribute('DICOM.instanceUIDs').split()
            return [slicer.dicomDatabase.fileForInstance(instanceUID) for instanceUID in instanceUIDs]

    def upload_file(self, hostid: str, local_file: str, remote_file: str):
        
        # make sure host_input_dir exists / create dir under tmp
        cmd = ["ssh", hostid, "mkdir", "-p", os.path.dirname(remote_file)]
        proc = slicer.util.launchConsoleProcess(cmd)
        slicer.util.logProcessOutput(proc)
        
        # upload the files to host
        cmd = ["scp", local_file, f"{hostid}:{remote_file}"]
        p = ProgressObserver(cmd, timeout=0)
        p.onStop(lambda t, rc: print(f"File upload done: {t}, {rc}"))

    def zip_node(self, node, zip_file: str, verbose: bool = True):
        """
        Create a zip file from a dicom image node at the specified location.
        """
        import zipfile
        
        # get list of all dicom files
        files = self.get_node_paths(node)
     
        # print number of files
        if verbose: print(f"number of files: {len(files)}")
        
        # check if the zip file exists
        if os.path.exists(zip_file):
            raise Exception(f"Zip file already exists: {zip_file}")
        
        # check if the path exists 
        if not os.path.exists(os.path.dirname(zip_file)):
            os.makedirs(os.path.dirname(zip_file))

        # make zip file under local input dir and add all files to it
        if verbose: print(f"creating zip file {zip_file}")
        with zipfile.ZipFile(zip_file, 'w') as zipMe:        
            for file in files:
                
                # print
                if verbose: print(f"adding file {file} to zip file")
                
                # compress the file
                zipMe.write(file, os.path.basename(file), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                
                # let slicer breathe :D
                slicer.app.processEvents()

    def onMhubRunStop(self, success: bool):
        print(f"Running MHUB DONE: {success}")

    def run_mhub(self, applyButton: qt.QPushButton, hostid: str, model: str, gpus: Optional[List[int]], host_dir: str, local_dir, local_in_zip: str, local_out_dir: str, timeout: int = 600):

        # create input and output folder on host
        host_input_dir = os.path.join(host_dir, "dicom")
        host_output_dir = os.path.join(host_dir, "results")
        host_output_zip = os.path.join(host_dir, "results.zip")
        local_output_zip = os.path.join(local_dir, "results.zip")

        # create async cmd process chain
        chain = ProcessChain()

        # create temp dir on host
        chain.add(["ssh", hostid, "mkdir", "-p", host_input_dir, host_output_dir], 
                  name="Create temp dir on host")

        # upload file to host
        chain.add(["scp", local_in_zip, f"{hostid}:{host_dir}/input.zip"],
                  name="Upload input file to host")
        
        # unzip file on host
        chain.add(["ssh", hostid, "unzip", f"{host_dir}/input.zip", "-d", host_input_dir],
                  name="Unzip input file on host")

        # gpus command
        mhub_run_gpus = [] if gpus is None or len(gpus) == 0 else ["--gpus", f"'\"device={','.join(str(i) for i in gpus)}\"'"]
        
        # run mhub
        chain.add([
            "ssh", hostid,
            "docker", "run", "--rm", "-t"
        ] + mhub_run_gpus + [
            "-v", f"{host_input_dir}:/app/data/input_data:ro",
            "-v", f"{host_output_dir}:/app/data/output_data:rw",
            f"mhubai/{model}:latest"
        ], name="Run mhub")
        
        # zip mhub output folder
        chain.add(["ssh", hostid, "zip", "-r", host_output_zip, host_output_dir],
                  name="Zip output folder on host")
        
        # download file from host
        chain.add(["scp", f"{hostid}:{host_output_zip}", local_output_zip],
                  name="Download output file from host")
        
        # unzip results on local machine
        chain.add(["unzip", local_output_zip, "-d", local_out_dir],
                  name="Unzip output file on local machine")
        
        # define callbacks
        def onMhubRunProgress(cmd: ProcessChain.CMD, time: int):
            #print(f"Running MHUB: {cmd.index}: {cmd.name} - {time}")
            applyButton.text = f"Running MHUB: {cmd.index}: {cmd.name} - {time}"
        
        # connect chain observer
        chain.onStop(self.onMhubRunStop)
        chain.onProgress(onMhubRunProgress)
        
        # print commands
        for cmd in chain.cmds:
            print(cmd.name)
            print(">", " ".join(cmd.cmd))
                
        # start the process chain
        #chain.start()
        
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

    def scanDirectoryForFilesWithExtension(self, local_dir: str, extension: str = ".seg.dcm") -> List[str]:
        """
        Find all files with the specified extension in the specified directory and its subdirectories.
        """
        seg_files = []
        for root, _, files in os.walk(local_dir):
            for file in files:
                if file.endswith(extension):
                    seg_files.append(os.path.join(root, file))
        return seg_files 

    def addFilesToDatabase(self, files: List[str], operation: Literal["reference", "copy", "move"]) -> None:
        # DICOM indexer uses the current DICOM database folder as the basis for relative paths,
        # therefore we must convert the folder path to absolute to ensure this code works
        # even when a relative path is used as self.extractedFilesDirectory.
        
        # get indexer
        indexer = ctk.ctkDICOMIndexer()
        
        # add files to database if operation is not 'reference'
        copyFile = operation in ["copy", "move"]
       
        # import files
        for file in files:
            indexer.addFile(slicer.dicomDatabase, os.path.abspath(file), copyFile)
            slicer.app.processEvents()
        
        # wait for the indexing to finish
        indexer.waitForImportFinished()
        
        # delete file if operation is 'move'
        if operation == "move":
            for file in files:
                os.remove(file)

    def importSegmentations(self, files: List[str]):
        import DICOMSegmentationPlugin
        
        # create importer
        importer = DICOMSegmentationPlugin.DICOMSegmentationPluginClass()

        # examine files
        loadables = importer.examineFiles(files)
        
        # import files
        for loadable in loadables:
            importer.load(loadable)

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



# TODO: get gpus and allow select-box passed to docker command