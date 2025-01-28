import logging
import os
from typing import Annotated, Any, Optional, List, Callable, Literal, Dict
from dataclasses import dataclass
import tempfile

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
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
        self.ui.cancelButton.connect('clicked(bool)', self.onCancelButton)
        self.ui.cmdKillObservedProcesses.connect('clicked(bool)', self.onKillObservedProcessesButton)
        self.ui.cmdBackendReload.connect('clicked(bool)', self.onBackendUpdate)
        self.ui.cmdInstallUdocker.connect('clicked(bool)', self.logic.installUdockerBackend)
        self.ui.cmdInstallUdocker.enabled = False
        # self.ui.cmdTest.connect('clicked(bool)', self.importSegmentations)
        self.ui.cmdReloadHostGpus.connect('clicked(bool)', self.updateHostGpuList)
        self.ui.chkGpuEnabled.connect('clicked(bool)', self.onGpuEnabled)
        self.ui.lstBackendImages.connect('itemSelectionChanged()', self.onBackendImageSelect)
        self.ui.cmdImageUpdate.connect('clicked(bool)', self.onBackendImageUpdate)
        self.ui.cmdImageRemove.connect('clicked(bool)', self.onBackendImageRemove)
                
        # search box "searchModel" and model list "lstModelList"
        self.ui.searchModel.textChanged.connect(self.onSearchModel)
        #self.ui.lstModelList.connect('itemSelectionChanged()', self.onModelSelect)
        self.ui.tblModelList.connect('cellClicked(int, int)', self.onModelSelectFromTable)
        self.onSearchModel("")
                
        # Dropdowns
        self.ui.backendSelector.addItems(["docker", "udocker"])
        self.ui.backendSelector.connect('currentIndexChanged(int)', self.onBackendSelect)

        # executable paths
        self.ui.pthDockerExecutable.currentPath = self.logic.getDockerExecutable()
        self.ui.pthUDockerExecutable.currentPath = self.logic.getUDockerExecutable()
        self.ui.pthDockerExecutable.connect('currentPathChanged(QString)', self.onUpdateDockerExecutable)
        self.ui.pthUDockerExecutable.connect('currentPathChanged(QString)', self.onUpdateUDockerExecutable)
        self.ui.cmdDetectDockerExecutable.connect('clicked(bool)', self.onAutoDetectDockerExecutable)
        self.ui.cmdDetectUDockerExecutable.connect('clicked(bool)', self.onAutoDetectUDockerExecutable)

        # setup SubjectHierarchyTreeView
        # -> https://apidocs.slicer.org/v4.8/classqMRMLSubjectHierarchyTreeView.html#a3214047490b8efd11dc9abf59c646495
        self.ui.SubjectHierarchyTreeView.setMRMLScene(slicer.mrmlScene)
        self.ui.SubjectHierarchyTreeView.connect('currentItemChanged(vtkIdType)', self.onSubjectHierarchyTreeViewCurrentItemChanged)

        # input node
        # self.ui.inputSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onInputNodeSelect)

        # load model repo
        # self.ui.modelSelector.connect('currentIndexChanged(int)', self.onModelSelect)
        # models = self.logic.getModels()
        # self.ui.modelSelector.clear()
        # for model in models:
        #     self.ui.modelSelector.addItem(model)

        # load gpus
        self.updateHostGpuList()
            
        # load backends
        self.onBackendSelect(0)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()
        
        # print path
        import sys
        print(sys.path)
        
        # run which python and which pip 
        import subprocess
        print(subprocess.run(["which", "python3"], capture_output=True).stdout.decode('utf-8'))
        print(subprocess.run(["which", "udocker"], capture_output=True).stdout.decode('utf-8'))
        
        # try the same with slicer.utils.consoleProcess
        p = slicer.util.launchConsoleProcess(["which", "python3"])
        print(p.stdout.read())

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
        assert self.logic is not None
        
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Select default input nodes if nothing is selected yet to save a few clicks for the user
        if self._parameterNode and not self._parameterNode.inputVolume:
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


    def onSubjectHierarchyTreeViewCurrentItemChanged(self, itemId: int) -> None:
        
        # get subject hierarchy node
        shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)

        # print debug
        print("SubjectHierarchyTreeView currentItemChanged: ", itemId, shNode.GetItemName(itemId))

        # get the volume node
        volumeNode = shNode.GetItemDataNode(itemId)

        # update the (old) input selector based on selection
        if volumeNode:
            self.ui.inputSelector.setCurrentNode(volumeNode)
            self._checkCanApply()
            
        # --- multi selection: 
            
        # make vtkIdList
        items = vtk.vtkIdList()
            
        # multi selection
        self.ui.SubjectHierarchyTreeView.currentItems(items)

        # print all selected items
        for i in range(items.GetNumberOfIds()):
            print("Selected item: ", shNode.GetItemName(items.GetId(i)))

    def onUpdateDockerExecutable(self, path) -> None:
        assert self.logic is not None
        # user enters a new path for the docker executable manually
        
        # get docker executable
        docker_executable = self.ui.pthDockerExecutable.currentPath
        
        # set docker executable
        print("---docker_executable-->", docker_executable, path)
        self.logic._executables["docker"] = docker_executable
    
    def onAutoDetectDockerExecutable(self) -> None:
        assert self.logic is not None
        # user clicks on the detect button
        
        # get docker executable
        docker_executable = self.logic.getDockerExecutable(refresh=True)
        
        # set docker executable
        self.ui.pthDockerExecutable.currentPath = docker_executable
        
    def onUpdateUDockerExecutable(self, path) -> None:
        assert self.logic is not None
        # user enters a new path for the udocker executable manually
        
        # get udocker executable
        udocker_executable = self.ui.pthUDockerExecutable.currentPath
        
        # set udocker executable
        print("---udocker_executable-->", udocker_executable, path)
        self.logic._executables["udocker"] = udocker_executable
        
    def onAutoDetectUDockerExecutable(self) -> None:
        assert self.logic is not None
        # user clicks on the detect button
        
        # get udocker executable
        udocker_executable = self.logic.getUDockerExecutable(refresh=True)
        
        # set udocker executable
        self.ui.pthUDockerExecutable.currentPath = udocker_executable

    def _checkCanApply(self, caller=None, event=None) -> None:
        
        # check if model is already running
        tasks = ProgressObserver.getTasksWhere(operation="run")
        if len(tasks) > 0:
            self.ui.cancelButton.enabled = True
            return
        self.ui.cancelButton.enabled = False
        
        # check if model is selected
        model = self.getModelFromTableSelection()
        
        # check if backend is selected / available
        # TODO: ...
        
        # chekc if gpu requirements are met
        # TODO: ...
                
        # check if input is selected
        if model and model.inputs_compatibility and self._parameterNode and self._parameterNode.inputVolume:
            self.ui.applyButton.toolTip = _("Compute output volume")
            self.ui.applyButton.enabled = True
            self.ui.applyButton.text = f"Run {model.label}"
        else:
            self.ui.applyButton.toolTip = _("Select input volume node")
            self.ui.applyButton.enabled = False
            
            if not model:
                self.ui.applyButton.text = "Select an MHub.ai Model"
            elif not self._parameterNode or not self._parameterNode.inputVolume:
                self.ui.applyButton.text = "Select an Input Volume"
            elif not model.inputs_compatibility:
                self.ui.applyButton.text = "Select a Model compatible with 3D Slicer Extension"
                self.ui.applyButton.toolTip = _("The 3D Slicer extension only supports segmentation models with a single DICOM input. For all other models, use the Web button to get more information on how you can run the model from the command line.")
            else:
                self.ui.applyButton.text = "N/A"
        

    def onKillObservedProcessesButton(self) -> None:
        """
        Run processing when user clicks "Kill Observed Processes" button.
        """
        
        # values
        num_tasks = len(ProgressObserver._tasks)
        details = "\n".join(["- " + " ".join(task.cmd) + "\n>" + str(task.data) + "\n" for task in ProgressObserver._tasks])
        
        # display message box
        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Warning)
        msg.setWindowTitle("Kill Observed Processes")
        msg.setText(f"Do you want to kill {num_tasks} observed processes?")
        msg.setDetailedText(details)
        msg.setStandardButtons(qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
        msg.setDefaultButton(qt.QMessageBox.Cancel)
        ret = msg.exec_()
        
        if ret != qt.QMessageBox.Ok:
            return
        
        # kill all observed processes
        ProgressObserver.killAll()

    def updateHostGpuList(self) -> None:
        assert self.logic is not None
        
        gpus = self.logic.getGPUInformation()
        for gpu in gpus:
            self.ui.lstHostGpu.addItem(gpu)
        self.ui.chkGpuEnabled.checked = len(gpus) > 0
        self.ui.chkGpuEnabled.enabled = len(gpus) > 0

    def onGpuEnabled(self) -> None:
        
        # enable/disable gpus
        enabled = self.ui.chkGpuEnabled.checked
        self.ui.lstHostGpu.enabled = enabled
        
        # enable/disable apply button
        self._checkCanApply()

    def loadModelRepo(self) -> None:
        pass
    
    def onSearchModel(self, text: str) -> None:
        assert self.logic is not None
        print("Search model: ", text)
            
        # get models 
        models = self.logic.getModels()
            
        # filter models
        models = [model for model in models if model.str_match(text)]
        
        # update model list
        # self.ui.lstModelList.clear()
        # for model in models:
        #     self.ui.lstModelList.addItem(model)
            
        # set table height to 10 rows
        self.ui.tblModelList.setRowCount(10)
                    
        # remove all rows from model table
        self.ui.tblModelList.setRowCount(0)

        # add models to table with 3 columns
        self.ui.tblModelList.setColumnCount(4)
        self.ui.tblModelList.setHorizontalHeaderLabels(["Model", "Type", "Image", "Actions"])

        # make table rows slim
        self.ui.tblModelList.verticalHeader().setDefaultSectionSize(20)
        
        # make table columns use all available space
        self.ui.tblModelList.horizontalHeader().setStretchLastSection(True)
        
        # select full row when cell is clicked
        self.ui.tblModelList.setSelectionBehavior(qt.QAbstractItemView.SelectRows)
        
        # make first column (model label) stretchable
        # NOTE: makes label column un-editable - not the best UX?!
        self.ui.tblModelList.horizontalHeader().setSectionResizeMode(0, qt.QHeaderView.Stretch)
        
        # fill table with models that match the search text
        for model in models:
            rowPosition = self.ui.tblModelList.rowCount
            self.ui.tblModelList.insertRow(rowPosition)
                        
            # add model name
            label_item = qt.QTableWidgetItem(model.label)
            label_item.setData(qt.Qt.UserRole, model)
            self.ui.tblModelList.setItem(rowPosition, 0, label_item)
                        
            # add model type (placeholder)
            self.ui.tblModelList.setItem(rowPosition, 1, qt.QTableWidgetItem(",".join(model.categories)))
            
            # add model image (placeholder) 
            self.ui.tblModelList.setItem(rowPosition, 2, qt.QTableWidgetItem(",".join(model.modalities)))
            
            # create horizontal layout, add pull, run, and details buttons, and set layout to cell
            layout = qt.QHBoxLayout()
            layout.setSpacing(0)
            layout.setContentsMargins(0,0,0,0)
            
            # Create function that creates a new scope for each button
            def create_pull_handler(btnPull, model):
                return lambda: self.onModelPull(btnPull, model)

            # def create_run_handler(btnRun, model):
            #     return lambda: self.onModelRun(btnRun, model)

            def create_details_handler(model):
                return lambda: self.onModelDetails(model)
            
            def create_web_handler(model):
                return lambda: self.onModelWeb(model)

            btnPull = qt.QPushButton("Pull")
            btnPull.clicked.connect(create_pull_handler(btnPull, model))
            layout.addWidget(btnPull)
            
            # disable pull button if image is available locally
            images = self.logic.getLocalImages("docker", cached=True)
            images = [i.split()[0] for i in images]
            model_image_name = f"mhubai/{model.name}:latest"
            print(images, model_image_name)
            if model_image_name in images:
                btnPull.enabled = False
                btnPull.text = "Pulled"
                btnPull.toolTip = "Image is available locally"

            # btnRun = qt.QPushButton("Run")
            # btnRun.clicked.connect(create_run_handler(btnRun, model))
            # layout.addWidget(btnRun)

            btnDetails = qt.QPushButton("Details")
            btnDetails.clicked.connect(create_details_handler(model))
            layout.addWidget(btnDetails)

            btnWeb = qt.QPushButton("Web")
            btnWeb.clicked.connect(create_web_handler(model))
            layout.addWidget(btnWeb)
            
            widget = qt.QWidget()
            widget.setLayout(layout)
            self.ui.tblModelList.setCellWidget(rowPosition, 3, widget)
            
            # if model has more than 1 input, disable row
            if not model.inputs_compatibility:
                for ci in range(4):
                    item = self.ui.tblModelList.item(rowPosition, ci)
                    if item:
                        item.setFlags(item.flags() & ~qt.Qt.ItemIsEditable)  # Make it non-editable
                        item.setBackground(qt.Qt.gray)  # Change background color to indicate it's disabled
                        item.setForeground(qt.Qt.white)  # Change text color to white
                
            
    def onModelDetails(self, model: 'Model') -> None:
        
        # get model
        #model = self.logic.getModel(model_name)
        
        # helper to generate headline-list strings
        def hlst(headline: str, items: list[str]) -> str:
            return f"{headline}:\n" +  "\n".join([f"  - {item}" for item in items])
        
        # generate model details string    
        details = [model.label]
        details += [model.description]
        details += [hlst("Modalities", model.modalities)]
        details += [hlst("Categories", model.categories)]
        details += [hlst("Inputs", model.inputs)]
        
        # display popup with model details
        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Information)
        msg.setWindowTitle(model.label)
        msg.setText(model.description)
        msg.setDetailedText("\n\n".join(details))
        
        # add buttons
        msg.addButton(qt.QMessageBox.Ok)
        
        # show message box
        msg.exec()
        
            
    def onModelWeb(self, model: 'Model') -> None:
        
        # open model in web
        url = qt.QUrl("https://mhub.ai/models/" + model.name)  
        qt.QDesktopServices.openUrl(url)
  
        
    def onModelPull(self, button: qt.QPushButton, model: 'Model') -> None:
        assert self.logic is not None
        
        # disable button and block table selection signals temporarily
        button.enabled = False
        
        # set button text to pulling
        button.text = "Pulling..."
        
        # construct image name
        image_name = f"mhubai/{model.name}:latest"
        
        # debug
        print("Pulling image: ", image_name)
        
        # on stop handler
        def on_stop(*args):
            # button.enabled = True
            button.text = "Pulled" # <-- NOTE: optimistic update
            self.updateBackendImagesList()
            
            # debug
            print(f"Image {image_name} pulled, args: {args}")
        
        # pull model
        self.logic.update_image(image_name, on_stop=on_stop)
           
    def onModelLoadTest(self, model: str) -> None:
        
        # create temporary directory to store test data
        
        # run mhub.test and mount the temp directory into the /app/data/input_data
        
        # check if there are dicom files in the input directory
        
        # check if already in database
        # QUESTION: how?
        
        # import into database and load sample
        
        pass 
    
    def getModelFromTableSelection(self, row: Optional[int] = None) -> Optional['Model']:
        
        # get selected row
        row = self.ui.tblModelList.currentRow() if row is None else row
        
        # get model from row
        item = self.ui.tblModelList.item(row, 0)
        model = item.data(qt.Qt.UserRole) if item else None
        
        return model
        
    def onModelSelectFromTable(self, row: int, col: int) -> None:
        
        # get model name
        model = self.getModelFromTableSelection(row)
        model_name = model.name if model else "N/A"

        # debug
        print("Model selected: ", row, col, model_name)
        
        # update apply button
        self._checkCanApply()

    def onBackendSelect(self, index: int) -> None:
        self.onBackendUpdate()
        
    def onBackendUpdate(self) -> None:
        assert self.logic is not None
        
        # get selected backend
        backend = self.ui.backendSelector.currentText
        
        # get backend information
        bi = self.logic.getBackendInformation(backend)
        
        # get host version
        if not bi.available:
            self.ui.lblBackendVersion.setText("Selected backend not available.")
            
        else:
            self.ui.lblBackendVersion.setText(bi.version)
            
        # enable / disable gpus seclection based on backend
        self.ui.lstHostGpu.enabled = backend == "docker"
            
        # update install backend button and images list
        self.updateInstallUDockerBackendButtonState()
        self.updateBackendImagesList()
            
    def updateInstallUDockerBackendButtonState(self) -> None:
        assert self.logic
        
        if self.ui.backendSelector.currentText == "udocker":
            is_installed = self.logic.isUdockerBackendInstalled()
            self.ui.cmdInstallUdocker.enabled = True
            
            if is_installed:
                self.ui.cmdInstallUdocker.text = "uninstall"
            else:
                self.ui.cmdInstallUdocker.text = "install"
        else:
            self.ui.cmdInstallUdocker.enabled = False
        
    def onBackendImageSelect(self) -> None:
        
        # if no image selected, disable update and remove buttons
        selected = self.ui.lstBackendImages.currentItem()
        
        # check if selected item is enabled
        # FIXME: somehow, & operator didn't work with `selected.flags() & qt.Qt.ItemIsEnabled`, but as we set qt.Qt.ItemIsEnabled as the only flag, this should be ok at least for now.
        enabled = selected.flags() != qt.Qt.ItemIsEnabled
        
        # enable / disable image actions
        self.ui.cmdImageUpdate.enabled = selected is not None and enabled
        self.ui.cmdImageRemove.enabled = selected is not None and enabled
        
        # debug
        print(f"Selected image: {selected.text()}, status: {enabled}")
    
    def onBackendImageUpdate(self) -> None:
        assert self.logic

        # get selected image
        selected = self.ui.lstBackendImages.currentItem()
        image_name = selected.text()
        
        # debug
        print(f"Updating image: {image_name}")
        
        # show a message box
        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Warning)
        msg.setText(f"Do you want to update image {image_name}?")
        msg.setWindowTitle("Update image")
        msg.setStandardButtons(qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
        msg.setDefaultButton(qt.QMessageBox.Cancel)
        ret = msg.exec_()
        
        if ret != qt.QMessageBox.Ok:
            return
        
        # debug
        print("Updating image")
        
        # add `updating...` to image and disable entry
        selected.setText(f"{image_name} (updating...)")
        selected.setFlags(qt.Qt.ItemIsEnabled)
        
        # on stop callback removes `updating...` from image
        def on_stop(*args):
            selected.setText(image_name)
            
        # update image
        self.logic.update_image(image_name, on_stop=on_stop)
    
    def onBackendImageRemove(self) -> None:
        assert self.logic
        
        # get selected image
        selected = self.ui.lstBackendImages.currentItem()
        image_name = selected.text()
        
        # debug
        print(f"Removing image: {image_name}")
        
        # show a message box
        msg = qt.QMessageBox()
        msg.setIcon(qt.QMessageBox.Warning)
        msg.setText(f"Do you want to remove image {image_name}?")
        msg.setWindowTitle("Remove image")
        msg.setStandardButtons(qt.QMessageBox.Ok | qt.QMessageBox.Cancel)
        msg.setDefaultButton(qt.QMessageBox.Cancel)
        ret = msg.exec_()
        
        if ret != qt.QMessageBox.Ok:
            return
        
        # debug
        print("Removing image")
        
        # add `removing...` to image and disable entry
        selected.setText(f"{image_name} (removing...)")
        selected.setFlags(qt.Qt.ItemIsEnabled)
        
        # on stop callback removes entry
        def on_stop(errorcode: int, stdout: str, *args):
            
            # debug
            print(f"/ Image {image_name} removed \\")            
            print(stdout)
            print(f"\\ Image {image_name} removed (errorCode: {errorcode}) /")            
            
            # FIXME: this is very optimistic...
            self.ui.lstBackendImages.takeItem(self.ui.lstBackendImages.row(selected))
        
        # remove image
        self.logic.remove_image(image_name, on_stop=on_stop)

    def updateBackendImagesList(self) -> None:
        assert self.logic is not None
        
        # get selected backend
        backend = self.ui.backendSelector.currentText
        
        # get available images
        images = self.logic.getLocalImages(backend, cached=False)
        
        # update list
        self.ui.lstBackendImages.clear()
        for image in images:
            item = qt.QListWidgetItem()
            item.setText(image)
            self.ui.lstBackendImages.addItem(item)

    # def initiateHostTest(self) -> None:
    #     assert self.logic is not None
        
    #     def onStart():
    #         self.ui.lblHostTestStatus.setText("Testing.")
    #         self.ui.hostSelector.enabled = False
    #         self.ui.cmdTestHost.enabled = False
        
    #     def onProgress(progress: int):
    #         self.ui.lblHostTestStatus.setText(f"Testing ({progress}s)")
        
    #     def onStop():
    #         self.ui.hostSelector.enabled = True
    #         self.ui.cmdTestHost.enabled = True
    #         self.ui.lblHostTestStatus.setText("Done.")

    #         # update host information
    #         self.updateHostInfo()
            
    #     self.logic.testSshHost(self.ui.hostSelector.currentText, onStart, onProgress, onStop)

    # def onTestHostButton(self) -> None:
    #     """
    #     Run processing when user clicks "Test Host" button.
    #     """
            
    #     self.initiateHostTest()
    
    def onCancelButton(self) -> None:
        
        # search for the running process
        tasks = ProgressObserver.getTasksWhere(operation="run")
        assert len(tasks) <= 1, "Multiple tasks running"
        assert len(tasks) > 0, "No task running"
        
        # get task
        task = tasks[0]
        
        # kill task
        task.kill()
    
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
        
        # deactivate apply button and activate cancel button
        self.ui.applyButton.enabled = False
        self.ui.cancelButton.enabled = True
        
        # get backend
        backend = self.ui.backendSelector.currentText
        
        ###### TEST (for caching on host)
        # get InstanceUIDs (only available for nodes loaded through the dicom module)
        node = self.ui.inputSelector.currentNode()
        instanceUIDs = node.GetAttribute('DICOM.instanceUIDs')

        # create hash from instanceUIDs
        hash = hashlib.sha256()
        hash.update(instanceUIDs.encode('utf-8'))
        instance_idh = hash.hexdigest()

        # get selected model
        model = self.getModelFromTableSelection()
        assert model is not None, "No model selected"

        print(instance_idh)
    
        with slicer.util.tryWithErrorDisplay(_("Failed to compute results."), waitCursor=True):
            assert self.logic is not None
            
            import shutil
            
            tmp_dir = "/tmp/mhub_slicer_extension"
            #tmp_dir = "/Users/lenny/Projects/SlicerMHubIntegration/SlicerMHubRunner/return_data"
            input_dir = os.path.join(tmp_dir, "input")
            output_dir = os.path.join(tmp_dir, "output")
            
            # if temp dir exists remove it
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
                
            # create temp dir with input and output dir
            os.makedirs(input_dir)
            os.makedirs(output_dir)
            
            # get selected gpus
            # TODO: make gpus None 
            gpus: Optional[List[int]] = None
            if self.ui.chkGpuEnabled.checked:
                gpus = []
                for i in range(self.ui.lstHostGpu.count):
                    item = self.ui.lstHostGpu.item(i)
                    if item.checkState() == qt.Qt.Checked:
                        print("Selected GPU: ", item.text())
                        gpus.append(i)
            
            # create temp directory for slicer-mhub under $HOME/.slicer-mhub
            self.logic.copy_node(
                self.ui.inputSelector.currentNode(),
                input_dir
            )
            
            # clear logs
            self.ui.txtLogs.clear()
            
            # update apply button elapsed time
            def onProgress(progress: float, stdout: Optional[str]):
                self.ui.applyButton.text = f"Running {model.label} ({progress}s)"
                
                
                # display stdout in txtLogs
                if stdout is not None and stdout.strip() != "":
                    self.ui.txtLogs.appendPlainText(stdout)
                   
            def onStop(returncode: int, stdout: str, timedout: bool, killed: bool):
                
                # show message box
                msg = qt.QMessageBox()
                
                # set message box icon
                if returncode == 0:
                    msg.setIcon(qt.QMessageBox.Information)
                else:
                    msg.setIcon(qt.QMessageBox.Warning)
                    
                # set message box title
                msg.setWindowTitle(f"Terminated {model.label}")
                
                # set message box text
                model_image_name = f"mhubai/{model.name}:latest"
                text = f"Running {model.label} ({model_image_name}) finished with return code {returncode}."
                if timedout:
                    text += "\nProcess timed out."
                if killed:
                    text += "\nProcess killed."
                msg.setText(text)
                                
                # set message box detailed text
                msg.setDetailedText(stdout)
                
                # add buttons
                msg.addButton(qt.QMessageBox.Ok)
                
                # show message box
                msg.exec()
                
                # update run button
                self._checkCanApply()
                
            #
            self.logic.run_mhub(
                model=model.name,
                backend=backend,
                gpus=gpus,
                input_dir=input_dir,
                output_dir=output_dir,
                onProgress=onProgress,
                onStop=onStop
            )
            
       
#
# Asynchronous class for ssh operations
#

# class AsyncTask:
    
#     timer: qt.QTimer
#     timeout: int = 20           # seconds
#     progress: int = 0           # seconds
    
#     def __init__(self):        
#         # create qt timer
#         self.timer = qt.QTimer()
#         self.timer.setInterval(100)
#         self.timer.timeout.connect(self.onTimeout)
        
#     def onTimeout(self):
#         # update progress
#         self.progress += 1
#         if self.progress >= self.timeout * 10:
#             self.onStop()
#             self.timer.stop()
        
#         # cheak if thread stopped
#         if not self.thread.is_alive():
#             self.onStop()
#             self.timer.stop()
            
#         # call onProgress
#         self.onProgress(int(self.progress / 10))
        
#     def start(self):
#         self.beforeStart()
#         self.timer.start()
#         self.thread.start()
#         #self.work(*self.work_args, **self.work_kwargs)
#         self.onStart()
        
#     def setup(self, *args, **kwargs):
#         import threading
#         self.work_args = args
#         self.work_kwargs = kwargs
#         self.thread = threading.Thread(target=self.work, args=args, kwargs=kwargs, daemon=False)

#     def beforeStart(self):
#         pass

#     def onStart(self):
#         pass
    
#     def onProgress(self, progress: int):
#         pass

#     def work(self):
#         pass
    
#     def onStop(self):
#         pass

@dataclass
class Model:
    id: str
    name: str
    label: str
    description: str    
    modalities: list[str]
    categories: list[str]
    roi: list[str]
    
    inputs: list[str]
    inputs_compatibility: bool
    
    def str_match(self, text: str) -> bool:
        tl = text.lower()
        if tl in self.name.lower() or tl in self.label.lower() or tl in self.description.lower():
            return True
        if any([tl in r.lower() for r in self.roi]):
            return True
        if any([tl in m.lower() for m in self.modalities]):
            return True
        if any([tl in c.lower() for c in self.categories]):
            return True
        return False
    
# @dataclass
# class HostInformation:
#     name: str
#     canConnect: bool
#     testedOn: datetime
    
#     dockerVersion: str
#     gpus: List[str]
#     cachedSubjects: List[str]

@dataclass
class BackendInformation:
    name: str
    version: str
    available: bool

# class SSHHHelper(AsyncTask):
    
#     # run various asynchroneous tests and retrieve information from host
#     # - test: host availability (except localhost)
#     # - test: docker availability
#     # - get:  docker version
#     # - test: docker version (optional)
#     # - get:  available mhub images (all starting with mhubai/... except base)
    
#     timeout: int = 100           # seconds
    
#     # status variables (set from worker thread and read from main thread)
#     messages: List[str] = []
#     canConnect: bool = False
#     dockerVersion: str = "N/A"
#     gpus: List[str] = []
#     cache: List[str] = []
    
#     # callbacks
#     _onStart: Optional[Callable[[], None]] = None
#     _onProgress: Optional[Callable[[int], None]] = None
#     _onStop: Optional[Callable[[HostInformation], None]] = None
    
#     def setup(self, hostid: str):
#         super().setup(hostid=hostid)
#         self.hostid = hostid
       
#     def setOnStart(self, callback: Callable[[], None]):
#         self._onStart = callback
        
#     def setOnProgress(self, callback: Callable[[int], None]):
#         self._onProgress = callback
        
#     def setOnStop(self, callback: Callable[[HostInformation], None]):
#         self._onStop = callback
       
#     def onStart(self):
#         # invoke callback if defined
#         if self._onStart:
#             self._onStart()
       
#     def onProgress(self, progress: int):
#         # invoke callback if defined
#         if self._onProgress:
#             self._onProgress(progress)
       
#     def onStop(self):
       
#         # compile host information
#         hostInfo = HostInformation(
#             name=self.hostid,
#             canConnect=self.canConnect,
#             testedOn=datetime.now(),
#             dockerVersion=self.dockerVersion,
#             gpus=self.gpus,
#             cachedSubjects=self.cache
#         )
        
#         # invoke callback if defined
#         if self._onStop:
#             self._onStop(hostInfo)
       
#     def work(self, hostid: str):
#         import subprocess
        
#         # try connection
#         if hostid == "localhost":
#             self.canConnect = True
#         else:
#             try:
#                 subprocess.run(["ssh", hostid, "exit"], timeout=5, check=True)
#                 self.canConnect = True
#             except Exception as e:
#                 self.canConnect = False
#                 self.messages.append(f"Failed to connect to host: {hostid}: {e}")
                
#         # get docker version
#         if hostid == "localhost":
#             try:
#                 result = subprocess.run(["docker", "--version"], timeout=5, check=True, capture_output=True)
#                 self.dockerVersion = result.stdout.decode('utf-8')
#             except Exception as e:
#                 self.dockerVersion = "E"
#                 self.messages.append(f"Failed to get docker version: {e}")  
#         elif self.canConnect:        
#             try:
#                 result = subprocess.run(["ssh", hostid, "docker --version"], timeout=5, check=True, capture_output=True)
#                 self.dockerVersion = result.stdout.decode('utf-8')
#             except Exception as e:
#                 self.dockerVersion = "E"
#                 self.messages.append(f"Failed to get docker version: {e}")

#         # get gpus list
#         if hostid == "localhost":
#             try:
#                 result = subprocess.run(["nvidia-smi", "--list-gpus"], timeout=5, check=True, capture_output=True)
#                 self.gpus = result.stdout.decode('utf-8').split("\n")
#             except Exception as e:
#                 self.gpus = []
#                 self.messages.append(f"Failed to get gpus: {e}")
#         elif self.canConnect:        
#             try:
#                 result = subprocess.run(["ssh", hostid, "nvidia-smi", "--list-gpus"], timeout=5, check=True, capture_output=True)
#                 self.gpus = result.stdout.decode('utf-8').split("\n")
#             except Exception as e:
#                 self.gpus = []
#                 self.messages.append(f"Failed to get gpus: {e}")

#         # check cached subjects (directory names in /tmp/mhub_slicer_extension)
#         host_base = "/tmp/mhub_slicer_extension"
#         if hostid == "localhost": 
#             self.cache = os.listdir(host_base)
#         elif self.canConnect:
#             try: 
#                 result = subprocess.run(["ssh", hostid, f"ls {host_base}"], timeout=5, check=True, capture_output=True)
#                 self.cache = result.stdout.decode('utf-8').split("\n")
#             except Exception as e:
#                 self.cache = []
#                 self.messages.append(f"Failed to get cache: {e}")

class ProgressObserver:
    
    # # variables
    # _timeout: int = 0
    # _timer: qt.QTimer
    # _proc = None
    
    # # callbacks
    # _onProgress: Optional[Callable[[int, str], None]] = None
    # _onStop: Optional[Callable[[int, str, bool, bool], None]] = None
    
    # keep track of all running tasks
    _tasks: List['ProgressObserver'] = []
    
    @classmethod
    def killAll(cls):
        for task in cls._tasks:
            task.kill()
            
    @classmethod
    def getTasksWhere(cls, include_disabled: bool = False, **kwargs):
        matched_tasks = []
        for task in cls._tasks:
            
            if task.data is None: 
                continue
            
            if not include_disabled and task._disabled:
                continue
            
            match = True
            for key, value in kwargs.items():
                if key not in task.data or task.data[key] != value:
                    match = False
                    break
        
            if match:
                matched_tasks.append(task)
        
        return matched_tasks
    
    def __init__(self, cmd: List[str], frequency: float = 2, timeout: int = 0, data: Optional[Dict[str, Any]] = None):
        """
        cmd:       command to execute in subprocess
        frequency: progress update frequency in Hz
        timeout:   timeout in seconds, 0 means no timeout
        """
        
        # identifiers / cache 
        self.cmd = cmd
        self.data = data
        
        # set variables
        self._disabled = False
        self._timeout = timeout
        self._frequency = frequency
        self._seconds_elapsed = 0.0
        
        self._proc = None
        self._onProgress: Optional[Callable[[float, str], None]] = None
        self._onStop: Optional[Callable[[int, str, bool, bool], None]] = None
        
        # initialize timer
        self._timer: qt.QTimer = qt.QTimer()
        self._timer.setInterval(1000/frequency)
        self._timer.timeout.connect(self._onTimeout)
        
        # create a temp file for stdout
        stdout_file = tempfile.NamedTemporaryFile(delete=False, prefix="mhub_slicer_stdout_", suffix=".txt")
        stdout_file.close()
        
        print("Temp File Created: ", stdout_file.name)
        self._stdout_file_name = stdout_file.name
    
        # create empty file
        with open(stdout_file.name, 'w') as f:
            f.write("")
            
        # print if file exists
        print("Temp File Exists: ", self._stdout_file_name, os.path.exists(self._stdout_file_name))
        self._stdout_readpointer = 0
        
        # run command
        self._run(cmd)
        
        # add to tasks
        self._tasks.append(self)
        
    def _run(self, cmd: List[str]):
        import subprocess
        
        # run command
        self._proc = subprocess.Popen(
            cmd, 
            stdout=open(self._stdout_file_name, 'w', encoding='utf-8'), 
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        # start timer
        self._timer.start()

    def _stop(self, returncode: int, timedout: bool, killed: bool):
        
        # cleanup (delete stdout file)
        print("read and remove temp stdout file", self._stdout_file_name, os.path.exists(self._stdout_file_name))

        # retrieve stdout
        with open(self._stdout_file_name, 'r', encoding='utf-8') as f:
            stdout = f.read()

        # remove file
        os.remove(self._stdout_file_name)

        # stop callback
        if self._onStop:
            self._onStop(returncode, stdout, timedout, killed)

    def _onTimeout(self):
        assert self._proc is not None
        
        # skip if disabled
        if self._disabled:
            return
        
        # update time
        self._seconds_elapsed += 1.0 / self._frequency
        
        # check timeout condition
        if self._timeout > 0 and self._seconds_elapsed > self._timeout:
            self._timer.stop()
            self._proc.kill()
            self._stop(-1, True, False)
            self._tasks.remove(self)
            return
        
        # stop timer if process is done
        if self._proc.poll() is not None:
            returncode = self._proc.returncode
            self._timer.stop()
            self._stop(returncode, False, False)
            self._tasks.remove(self)
            return

        # call progress method
        if self._onProgress:
                        
            # fetch the latest process stdout from file
            with open(self._stdout_file_name, 'r', encoding='utf-8') as f:
                f.seek(self._stdout_readpointer)
                stdout = f.read()
                self._stdout_readpointer = f.tell()
            
            # call progress callback
            self._onProgress(self._seconds_elapsed, stdout)

    def onStop(self, callback: Callable[[int, str, bool, bool], None]):
        self._onStop = callback
        
    def onProgress(self, callback: Callable[[float, str], None]):
        self._onProgress = callback

    def kill(self):
        
        # disable
        self._disabled = True
        
        # stop the timer
        self._timer.stop()
        
        # try to stop 
        try:
            self._stop(-1, False, True)
        except Exception as e:
            print("Error when killing process: stop method failed. ", self.cmd, e)
            
        # then stop timer, kill process and remove from tasks
        if self._proc is not None:
            self._proc.kill()
            
        # remove from tasks
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
        self._onProgress: Optional[Callable[['ProcessChain.CMD', float], None]] = None
        
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
       
    def _on_process_stop(self, returncode: int, stdout: str, timedout: bool, killed: bool):
        if timedout or killed or returncode != 0:
            self.success = False
            self.stopped = True
            
            # invoke callback if defined
            if self._onStop:
                self._onStop(False)
        else:
            self._start_next()
        
    def _on_process_progress(self, time: float, stdout: str):
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

    def onProgress(self, callback: Callable[['ProcessChain.CMD', float], None]):
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
        self._executables: Dict[str, str] = {}
        # self.hosts: List[str] = []
        # self.hostInfo: Dict[str, HostInformation] = {}

        # load available hosts
        # self.getAvailableSshHosts()

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
        
    def getModel(self, model_name: str) -> Model:
        
        # get models
        models = self.getModels()
        
        # find model
        model = next((m for m in models if m.name == model_name), None)
        
        # error if not available
        if model is None:
            raise ValueError(f"Model not found: {model_name}")
        
        # return
        return model
        
    def getModels(self, cached: bool = True) -> List[Model]:
        import requests, json
        
        # return from cache if available
        if cached and hasattr(self, "_model_cache"):
            return self._model_cache
        
        # download model information from api endpoint (json)
        # -> migrate from https://mhub.ai/api/v2/models to https://mhub.ai/api/v2/models/detailed
        MHUBAI_API_ENDPOINT_MODELS = "https://mhub.ai/api/v2/models/detailed"
        
        # fetch
        response = requests.get(MHUBAI_API_ENDPOINT_MODELS)
        
        # parse
        payload = json.loads(response.text)
        
        # get model list
        models: List[Model] = []
        for model_data in payload['data']:
            
            # check if model inputs are compatible with slicer extension
            inputs_compatibility = len(model_data['inputs']) == 1 and all([i['format'].lower() == 'dicom' for i in model_data['inputs']]) and 'Segmentation' in model_data['categories']
            
            # create model
            models.append(Model(
                id=model_data['id'],
                name=model_data['name'],
                label=model_data['label'],
                description=model_data['description'],
                modalities=model_data['modalities'],
                roi=model_data['segmentations'],
                categories=model_data['categories'],
                inputs=[i['description'] for i in model_data['inputs']],
                inputs_compatibility=inputs_compatibility
            ))
            
        # cache
        self._model_cache = models

        # return
        return models
    
    def getDockerExecutable(self, refresh: bool = False) -> Optional[str]:
        import platform
        import subprocess

        if not refresh and "docker" in self._executables and self._executables["docker"]:
            return self._executables["docker"]
        
        # get operation system
        ops = platform.system()
                
        # find docker executable (windows, any linux, mac)
        docker_executable = None
        if ops == "Windows":
            docker_executable = "C:\Program Files\Docker\Docker"
        elif ops == "Darwin":
            docker_executable = "/usr/local/bin/docker"
        elif ops == "Linux":
            try:
                docker_executable = subprocess.run(["which", "docker"], capture_output=True).stdout.decode('utf-8').strip('\n')
            except Exception as e:
                pass
            
        # debug
        print("Docker executable: ", docker_executable)
            
        # error
        if docker_executable is None or docker_executable == "":
            print("WARNING: ", "Docker executable not found.")
        
        # cache
        if docker_executable:
            self._executables["docker"] = docker_executable
        
        # deliver
        return docker_executable
    
    def getUDockerExecutable(self, refresh: bool = False) -> Optional[str]:
        # TODO: return optional and display installation instructions under backend tab
        
        # TODO: figure out installation path.
        # TODO: pro/cons installing udocker in slicer vs. using system wide installation (also consider the nature of the tool)
        #return "/home/exouser/Downloads/Slicer-5.6.2-linux-amd64/lib/Python/bin/udocker" # <- linux: pip install executable
        #return "/home/exouser/Downloads/Slicer-5.6.2-linux-amd64/lib/Python/lib/python3.9/site-packages/udocker" # <- linux: pip install directory
        #return "/Applications/Slicer.app/Contents/lib/Python/bin/udocker" #  <- macos: pip install executable
    
        import platform
        import subprocess

        # cache lookup
        if not refresh and "udocker" in self._executables and self._executables["udocker"]:
            return self._executables["udocker"]

        # get operation system
        ops = platform.system()

        # find docker executable
        udocker_executable = None
        if ops == "Linux":
            try:
                udocker_executable = subprocess.run(["which", "udocker"], capture_output=True).stdout.decode('utf-8').strip('\n')
            except Exception as e:
                pass
            
        # debug
        print("U-Docker executable: ", udocker_executable)
            
        # error
        if udocker_executable is None or udocker_executable == "":
            print("WARNING: ", "U-Docker executable not found.")
        
        # cache
        if udocker_executable:
            self._executables["udocker"] = udocker_executable
        
        # deliver
        return udocker_executable
    
    def getBackendInformation(self, name: str) -> BackendInformation:
        assert name in ["docker", "udocker"]
        import subprocess, re
        
        # initialize bi
        bi = BackendInformation(name, "N/A", False)
        
        
        # fetch version and availability from backend     
        if name == "docker":
            try:
                docker_exec = self.getDockerExecutable()
                assert docker_exec is not None, "Docker executable not found"
                print("running" , docker_exec, "--version")
                result = subprocess.run([docker_exec, "--version"], timeout=5, check=True, capture_output=True)
                bi.version = result.stdout.decode('utf-8')
                bi.available = True
                print("Docker available")
            except Exception as e:
                bi.version = "E"
                bi.available = False
                
        elif name == "udocker":              
            try:
                # use launchConsoleProcess to run udocker --version
                # import udocker
                # bi.version = udocker.__version__ #proc.stdout.read().decode('utf-8')
                # bi.available = True
                
                # get udocker exec
                # TODO: check https://github.com/Slicer/Slicer/blob/9391c208f0d25a2fe2e6b19667766e759c6160c7/Base/Python/
                # slicer/util.py#L3857
                
                # run
                udocker_exec = self.getUDockerExecutable()
                assert udocker_exec is not None, "Udocker executable not found"
                print("running: ", udocker_exec, "--version")
                result = subprocess.run([udocker_exec, "--version"], timeout=5, check=True, capture_output=True)
                print("result: ", result.stdout.decode('utf-8'))
                
                # extract "version: x.x.x" from string
                version = re.search(r"version: ([0-9]+\.[0-9]+\.[0-9]+)", result.stdout.decode('utf-8'))
                
                bi.version = f"Version: {version.groups()[0]}" if version else "???"
                bi.available = True
                print("Udocker available")
                
            except Exception as e:
                bi.version = "E"
                bi.available = False
        
        # return 
        return bi
    
    def isUdockerBackendInstalled(self) -> bool:
        try:
            import udocker
            return True
        except ModuleNotFoundError as e:
            return False
    
    def installUdockerBackend(self):
        
        # chekc if udocker is already installed
        is_installed = self.isUdockerBackendInstalled()

        # install udocker in slicer
        if not is_installed:
            # install udocker
            slicer.util.pip_install('udocker')
            udocker_exec = self.getUDockerExecutable()
            
            # install additional dependencies
            slicer.util.launchConsoleProcess([udocker_exec, "install"]) # --force
        else:
            slicer.util.pip_uninstall('udocker')
        
    def getGPUInformation(self) -> List[str]:
        import subprocess
        
        # try to get gpus from nvidia-smi
        # TODO: extract additional version information from nvidia-smi 
        #       or have a separate availability cheecker for nvidia-smi
        try:
            result = subprocess.run(["nvidia-smi", "--list-gpus"], timeout=5, check=True, capture_output=True)
            gpus = result.stdout.decode('utf-8').split("\n")
        except Exception as e:
            gpus = []
            
        # return
        return gpus

    def getLocalImages(self, backend: str, cached: bool = True) -> List[str]:
        
        # get images
        import subprocess
        
        # cache
        if cached and hasattr(self, "_images_cache") and backend in self._images_cache:
            return self._images_cache[backend]
        
        # load images based on backend
        try:
            if backend == "docker":
                docker_exec = self.getDockerExecutable()
                assert docker_exec is not None, "Docker executable not found"
                result = subprocess.run([docker_exec, "images", "--filter", "reference=mhubai/*", "--format", "{{.Repository}}|{{.Tag}}|{{.Size}}"], timeout=5, check=True, capture_output=True)
                images = [i.split("|") for i in result.stdout.decode('utf-8').split("\n")]
                images = [f"{i[0]}:latest ({i[2]})" for i in images if len(i) == 3 and i[1] == "latest"]
                
            elif backend == "udocker":
                udocker_exec = self.getUDockerExecutable()
                assert udocker_exec is not None, "Udocker executable not found"
                result = subprocess.run([udocker_exec, "images"], timeout=5, check=True, capture_output=True)
                images = result.stdout.decode('utf-8').split("\n")
                images = [image.split()[0] for image in images if image.startswith("mhubai/")]
            
            # remove empty strings
            images = [image for image in images if image != ""]
            
        except Exception as e:
            images = []
            
        # cache
        if not hasattr(self, "_images_cache"):
            self._images_cache = {}
        self._images_cache[backend] = images
            
        # return
        return images
        
    def get_node_paths(self, node) -> List[str]:
        storageNode=node.GetStorageNode()
        if storageNode is not None:
            return [storageNode.GetFullNameFromFileName()]
        else:
            instanceUIDs=node.GetAttribute('DICOM.instanceUIDs').split()
            return [slicer.dicomDatabase.fileForInstance(instanceUID) for instanceUID in instanceUIDs]

    # def upload_file(self, hostid: str, local_file: str, remote_file: str):
        
    #     # make sure host_input_dir exists / create dir under tmp
    #     cmd = ["ssh", hostid, "mkdir", "-p", os.path.dirname(remote_file)]
    #     proc = slicer.util.launchConsoleProcess(cmd)
    #     slicer.util.logProcessOutput(proc)
        
    #     # upload the files to host
    #     cmd = ["scp", local_file, f"{hostid}:{remote_file}"]
    #     p = ProgressObserver(cmd, timeout=0)
    #     p.onStop(lambda t, rc: print(f"File upload done: {t}, {rc}"))

    # def zip_node(self, node, zip_file: str, verbose: bool = True):
    #     """
    #     Create a zip file from a dicom image node at the specified location.
    #     """
    #     import zipfile
        
    #     # get list of all dicom files
    #     files = self.get_node_paths(node)
     
    #     # print number of files
    #     if verbose: print(f"number of files: {len(files)}")
        
    #     # check if the zip file exists
    #     if os.path.exists(zip_file):
    #         raise Exception(f"Zip file already exists: {zip_file}")
        
    #     # check if the path exists 
    #     if not os.path.exists(os.path.dirname(zip_file)):
    #         os.makedirs(os.path.dirname(zip_file))

    #     # make zip file under local input dir and add all files to it
    #     if verbose: print(f"creating zip file {zip_file}")
    #     with zipfile.ZipFile(zip_file, 'w') as zipMe:        
    #         for file in files:
                
    #             # print
    #             if verbose: print(f"adding file {file} to zip file")
                
    #             # compress the file
    #             zipMe.write(file, os.path.basename(file), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                
    #             # let slicer breathe :D
    #             slicer.app.processEvents()

    def copy_node(self, node, copy_dir: str, verbose: bool = True):
        """
        Copy all dicom files from a dicom image node to the specified location.
        """
        import shutil
        
        # get list of all dicom files
        files = self.get_node_paths(node)
     
        # print number of files
        if verbose: 
            print(f"number of files: {len(files)}")
        
        # check if the path exists 
        if not os.path.exists(copy_dir):
            os.makedirs(copy_dir)
        
        # copy all files to the specified location
        for file in files:
            shutil.copy(file, copy_dir)
            
            # let slicer breathe :D
            slicer.app.processEvents()
       
    def _run_mhub_docker(self, model: str, gpus: Optional[List[int]], input_dir: str, output_dir: str, onProgress: Callable[[float, str], None], onStop: Callable[[int, str, bool, bool], None], timeout: int = 600):
        
        # gpus command
        if gpus is None:
            mhub_run_gpus = []
        elif len(gpus) == 0:
            mhub_run_gpus = ["--gpus", "all"]
        else:
            mhub_run_gpus = ["--gpus", f"'\"device={','.join(str(i) for i in gpus)}\"'"]
        
        # get executable
        docker_exec = self.getDockerExecutable()
        
        # run mhub
        run_cmd = [
            docker_exec, "run", "--rm", "-t", "--network=none"
        ] + mhub_run_gpus + [
            "-v", f"{input_dir}:/app/data/input_data:ro",
            "-v", f"{output_dir}:/app/data/output_data:rw",
            f"mhubai/{model}:latest",
            "--workflow",
            "default",
            "--print"
        ]
        
        # callback wrapper
        def _on_stop(returncode: int, stdout: str, timedout: bool, killed: bool):
            print(f"Command chain stopped with return code {returncode}. Timedout [{timedout}] Killed [{killed}]")
            onStop(returncode, stdout, timedout, killed)
        
        # run async
        po = ProgressObserver(run_cmd, frequency=2, timeout=timeout, data={"image_name": f"mhubai/{model}:latest", "operation": "run"})
        po.onStop(_on_stop)
        po.onProgress(onProgress)

    def _run_mhub_udocker(self, model: str, gpu: bool, input_dir: str, output_dir: str, onProgress: Callable[[float, str], None], onStop: Callable[[int, str, bool, bool], None], timeout: int = 600):
        
        # get executable
        udocker_exec = self.getUDockerExecutable()
        
        # callback wrapper
        def _on_progress(cmd: ProcessChain.CMD, time: float):
            #print(f"Command {cmd.name} running {time} seconds")
            onProgress(float(time), "")
            
        def _on_stop(success: bool):
            print(f"Command chain stopped with success: {success}")
            onStop(int(success), "", False, False)
        
        # initialize async processing chain
        pc = ProcessChain()
        pc.onStop(_on_stop)
        pc.onProgress(_on_progress)

        # setup gpu if required        
        if gpu:
            print("udocker with gpu")
            
            # check if image is already available or optionally pull image
            images = self.getLocalImages("udocker", cached=True)
            print(images)
            if f"mhubai/{model}:latest" not in images:
                pull_cmd = [udocker_exec, "pull", f"mhubai/{model}:latest"]
                pc.add(pull_cmd, name="Pull image")
            
            # create container
            create_cmd = [udocker_exec, "create", f"--name={model}", f"mhubai/{model}:latest"]
        
            # setup container
            setup_cmd = [udocker_exec, "setup", "--nvidia", "--force", model]
            
            # run container
            run_cmd = [udocker_exec, "run", "--rm", "-t", 
                       "-v", f"{input_dir}:/app/data/input_data:ro", 
                       "-v", f"{output_dir}:/app/data/output_data:rw", 
                       model]
        
            # processing chain
            pc.add(create_cmd, name="Create container")
            pc.add(setup_cmd, name="Setup container")
            pc.add(run_cmd, name="Run container")
            
            # print execution plan
            for cmd in pc.cmds:
                print(cmd.name, cmd.cmd)
        
        else:
            
            # run container
            run_cmd = [udocker_exec, "run", "--rm", "-t", 
                       "-v", f"{input_dir}:/app/data/input_data:ro", 
                       "-v", f"{output_dir}:/app/data/output_data:rw", 
                       f"mhubai/{model}:latest"]
        
            # processing chain
            pc.add(run_cmd, name="Run container")

            
        # run async
        pc.start()
                
    def run_mhub(self, 
                 model: str, 
                 backend: Literal["docker", "udocker"],
                 gpus: Optional[List[int]], 
                 input_dir: str, 
                 output_dir: str, 
                 onProgress: Optional[Callable[[float, str], None]] = None,
                 onStop: Optional[Callable[[int, str, bool, bool], None]] = None, 
                 timeout: int = 600):
                
        # define callbacks
        def _on_progress(time: float, stdout: str):
            
            # invoke onProgress callback
            if onProgress is not None and callable(onProgress): 
                onProgress(time, stdout)
                
        def _on_stop(returncode: int, stdout: str, timedout: bool, killed: bool):
        
            # import segmentations
            dsegfiles = self.scanDirectoryForFilesWithExtension(output_dir)
            self.addFilesToDatabase(dsegfiles, operation="copy")
            self.importSegmentations(dsegfiles)
        
            # invoke onStop callback
            if onStop is not None and callable(onStop): 
                onStop(returncode, stdout, timedout, killed)
        
        # run backend
        if backend == "docker":
            self._run_mhub_docker(model, gpus, input_dir, output_dir, _on_progress, _on_stop, timeout)
        elif backend == "udocker":
            self._run_mhub_udocker(model, gpus is not None, input_dir, output_dir, _on_progress, _on_stop, timeout)


    def remove_image(self, image_name, on_stop: Optional[Callable[[int, str, bool, bool], None]] = None, timeout: int = 0):
        
        # get docker executable
        docker_exec = self.getDockerExecutable()
        
        # remove image cli command
        cmd = [docker_exec, "rmi", image_name]
        
        # run command in bg
        po = ProgressObserver(cmd, frequency=2, timeout=timeout, data={"image_name": image_name, "operation": "remove"})
        if on_stop: po.onStop(on_stop)

    def update_image(self, image_name, on_stop: Optional[Callable[[int, str, bool, bool], None]] = None, timeout: int = 0):
        
        # get docker executable
        docker_exec = self.getDockerExecutable()
        
        # remove image cli command
        cmd = [docker_exec, "pull", image_name]
        
        # run command in bg
        po = ProgressObserver(cmd, frequency=2, timeout=timeout, data={"image_name": image_name, "operation": "update"})
        if on_stop: po.onStop(on_stop)
        
        # log output (DEBUG ONLY)
        def onProgress(t: float, stdout: str):
            print(f">> __pull image ({t})__")
            for line in stdout.split("\n"):
                print(f">> {line}")
                        
        po.onProgress(onProgress)
        

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