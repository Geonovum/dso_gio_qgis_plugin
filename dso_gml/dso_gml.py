# -*- coding: utf-8 -*-
"""
/***************************************************************************

                              DSO QGIS plugin

                              -------------------
        begin                : 2020-01-06
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Kasper Lingbeek
        email                : k.lingbeek@atos.net
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QDate
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from qgis.core import *

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .dso_gml_dialog import dsoGMLDialog

# xslt support
import lxml.etree as ET

import processing
from processing.core.Processing import Processing
Processing.initialize()

import os
import tempfile
import glob

import hashlib

from datetime import date
        
import uuid

class dsoGML:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'dsoGML_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
            
        self.dlg = dsoGMLDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&DSO GML')
        
        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('dsoGML', message)


    def add_action(self,icon_path,text,callback,enabled_flag=True,add_to_menu=True,
                    add_to_toolbar=True,status_tip=None,whats_this=None,parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/dso_gml/icon.png'
        self.add_action(icon_path,
                        text = self.tr(u'DSO GML'),
                        callback = self.run,
                        parent = self.iface.mainWindow())
        
        # will be set False in run()
        self.first_start = True
    
    def setNaam(self):
        # sets the 'Naam' to the layername
        # will be overwritten when there is an attribute 'Naam'
        try:
            new = self.dlg.mMapLayerComboBox.currentLayer().name()
            dir = os.path.dirname(self.dlg.mQgsFileWidget.filePath())
            if dir == '':
                dir = os.getcwd()
            QgsMessageLog.logMessage('Nieuwe naam: {}'.format(new), 'DSO GML', Qgis.Info)
            self.dlg.Naam.setText(new)
            self.dlg.mQgsFileWidget.setFilePath('{0}\{1}.gml'.format(dir,new.replace(' ','_')))
        except:pass
    
    def setLocatie(self):
        if self.dlg.atribuutwaardelijst.currentText() != '':
            self.dlg.Naam.setText(self.dlg.atribuutwaardelijst.currentText())

    def autoFill(self):
        # GIO-GML
        self.setLineEdit(self.dlg.Naam,'Naam',self.dlg.Naam.text())
        self.setLineEdit(self.dlg.FRBRExpression,'FRBRExpression','/join/id/regdata/')
        self.setLineEdit(self.dlg.Verwijzing,'Verwijzing','')
        self.setDateEdit(self.dlg.Actualiteit,'Actualiteit')
        
        # GIO-XML
        self.setLineEdit(self.dlg.Geboorteregeling,'Geboorteregeling','/akn/nl/act/')
        self.setLineEdit(self.dlg.Eindverantwoordelijke,'Eindverantwoordelijke','/tooi/id/')
        self.setLineEdit(self.dlg.Maker,'Maker','/tooi/id/')
        self.setLineEdit(self.dlg.OfficieleTitel,'Officiele titel','')
        self.setLineEdit(self.dlg.Alt_titel,'Alternatieve titel','')
        self.setLineEdit(self.dlg.OpvolgerVan,'Opvolger van','/join/id/regdata/')
        
    def setLineEdit(self, lineEdit, name, default):
        QgsMessageLog.logMessage('default: {}'.format(default), 'DSO GML', Qgis.Info)
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        try:
            # TODO: skip empty attributes
            value = layer.getFeature(1).attribute(name)
            # fill lineEdit with attribute value if exist else with default
            if value != '':
                lineEdit.setText(value)
            else:
                lineEdit.setText(default)
        except Exception as e:
            pass
    
    def setDateEdit(self, dateEdit, name):
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        try:
            if layer.fields().indexFromName(name)>-1:
                dateEdit.setDate(layer.getFeature(1).attribute(name))
        except:
            pass
    
    def fillAttributeList(self):
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        self.dlg.atribuutlijst.clear()
        self.dlg.atribuutwaardelijst.clear()
        try:
            self.dlg.atribuutlijst.addItems(layer.fields().names())
        except:
            pass
        
    def fillValueList(self):
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        attribute = self.dlg.atribuutlijst.currentIndex()
        id = self.dlg.atribuutlijst.currentIndex()
        self.dlg.atribuutwaardelijst.clear()
        try:
            self.dlg.atribuutwaardelijst.addItem('')
            self.dlg.atribuutwaardelijst.addItems(layer.uniqueValues(id,-1))
        except:
            pass
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.tr(u'&DSO GML'),action)
            self.iface.removeToolBarIcon(action)

    def createReprojectedLayer(self, layer, crs):
        """
        Creates a reprojected layer
        layer: layer used
        crs: crs used
        """
        temp = QgsVectorLayer('%s?crs=%s'% ('Multipolygon', crs.authid()), 'reproject.geojson', 'memory')
        if not layer.isValid():
            raise GeoAlgorithmExecutionException('Het herprojecteren van de laag is niet gelukt!')
            return None
        
        provider = temp.dataProvider()
        provider.addAttributes(layer.dataProvider().fields().toList())
        temp.updateFields()
        
        coordinateTransformer = QgsCoordinateTransform(QgsCoordinateReferenceSystem(QgsCoordinateReferenceSystem(layer.crs().authid())), QgsCoordinateReferenceSystem(QgsCoordinateReferenceSystem(crs)),QgsProject.instance())
        features = []
        for feature in layer.getFeatures():
            feat = QgsFeature(feature)
            geom = feat.geometry()
            geom.transform(coordinateTransformer)
            feat.setGeometry(geom)
            features.append(feat)
            
        provider.addFeatures(features)
        
        return temp

    def export_dso_gml(self):
        """ Exporteren van gekozen layer naar een GIO-GML voor het DSO """
        # parameters
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        layer_id = layer.id()
        output = self.dlg.mQgsFileWidget.filePath()
        layer_crs = layer.crs().authid()
        target_srs = self.dlg.mQgsProjectionSelectionWidget.crs()
        
        # maak een tijdelijke folder
        temp_dir = tempfile.mkdtemp('_dso-gml')
        # bewaar vorige cuurrent
        cwd_before = os.getcwd()
        # zet temp als current
        os.chdir(temp_dir)
        
        # opties voor opslaan instellen
        option_target_ns = '-dsco target_namespace="https://standaarden.overheid.nl/stop/imop/geo"'
        option_prefix = '-dsco prefix=geo'
        option_xsischema = '-dsco XSISCHEMA=OFF'
        option_xsischemauri = '-dsco XSISCHEMAURI="https://standaarden.overheid.nl/stop/imop/geo/ https://standaarden.overheid.nl/stop/1.0.4/imop-geo.xsd"'
        option_format = '-dsco FORMAT="GML3.2"'
        option_gml_feature_collection = '-dsco GML_FEATURE_COLLECTION=no'
        option_gml_id = '-dsco GML_ID="id-{}"'.format(uuid.uuid4())
        option_write_feature_bounded_by = '-dsco WRITE_FEATURE_BOUNDED_BY=no'
        
        # vaste naam aan layer geven, wordt geometry field naam
        nln = '-nln geometrie'
        nlt = '-nlt CONVERT_TO_LINEAR'
        
        # reproject naar opgegeven crs indien nodig
        if layer_crs != target_srs.authid():
            layer = self.createReprojectedLayer(layer, target_srs)
            layer_id = layer.id()
            reproject_layer = QgsProject.instance().addMapLayer(layer,False)

        if not layer.isValid():
            raise GeoAlgorithmExecutionException('Problema ao criar camada reprojetada!')
            return None
            
        QgsMessageLog.logMessage('layer id: {}'.format(layer_id), 'DSO GML', Qgis.Info)

        dsco = ' '.join([option_target_ns,
                         option_prefix,
                         option_xsischema,
                         option_xsischema,
                         option_xsischemauri,
                         option_format,
                         option_gml_feature_collection,
                         option_gml_id,
                         option_write_feature_bounded_by,
                         nln,
                         nlt])

        QgsMessageLog.logMessage(dsco, 'DSO GML', Qgis.Info)
        
        #test=processing.run("qgis:checkvalidity", {'INPUT_LAYER':layer_id,'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False,'VALID_OUTPUT':'TEMPORARY_OUTPUT','INVALID_OUTPUT':'TEMPORARY_OUTPUT','ERROR_OUTPUT':'TEMPORARY_OUTPUT'})
        
        # select features if atribuutlijst en atribuutwaardelijst is activated
        QgsMessageLog.logMessage('Filter: {}'.format(self.dlg.Filter.isChecked()), 'DSO GML', Qgis.Info)
        if self.dlg.Filter.isChecked() == 1:
            layer.selectByExpression("\"{0}\"=\'{1}\'".format(self.dlg.atribuutlijst.currentText(),self.dlg.atribuutwaardelijst.currentText()))

        # select all features if no features are selected
        if layer.selectedFeatureCount() == 0:
            layer.selectAll()
        
        if self.dlg.valide.checkState() == 2:
            try:QgsProject.instance().removeMapLayer(fix)
            except:pass
            layer_id=fix=processing.run("native:fixgeometries", {'INPUT':QgsProcessingFeatureSourceDefinition(layer_id, selectedFeaturesOnly=True, featureLimit=-1, geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),'OUTPUT':'fix.geojson'})['OUTPUT']
            #layer_id=fix=processing.run("native:fixgeometries", {'INPUT':layer_id, selectedFeaturesOnly=True,'OUTPUT':'fix.geojson'})['OUTPUT']

        if self.dlg.dissolve.checkState() == 2:
            layer_id=dissolve=processing.run("native:dissolve", {'INPUT':layer_id,'FIELD':[],'OUTPUT':'dissolve.geojson'})['OUTPUT']

        if self.dlg.snap.checkState() == 2:
            # get the numer of decimals
            dec_val = self.dlg.decimalen.value()
            num_dec = '1{}'.format('0'*dec_val)
            spacing = 1/float(num_dec)
            
            # repeat snap and fix until there are no errors
            test=1
            while test>0:
                try:QgsProject.instance().removeMapLayer(snap)
                except:pass
                layer_id = snap = processing.run("native:snappointstogrid", {'INPUT':layer_id,'HSPACING':spacing,'VSPACING':spacing,'ZSPACING':0,'MSPACING':0,'OUTPUT':'snap.geojson'})['OUTPUT']
                QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
                try:QgsProject.instance().removeMapLayer(fix)
                except:pass
                layer_id = fix = processing.run("native:fixgeometries", {'INPUT':layer_id,'OUTPUT':'fix2.geojson'})['OUTPUT']
                QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
                test = processing.run("qgis:checkvalidity", {'INPUT_LAYER':layer_id,'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False})['ERROR_COUNT']
                QgsMessageLog.logMessage('test: {}'.format(test), 'DSO GML', Qgis.Info)
            
        if self.dlg.valide.checkState() == 2:
            try:QgsProject.instance().removeMapLayer(fix)
            except:pass
            layer_id = fix = processing.run("native:fixgeometries", {'INPUT':layer_id,'OUTPUT':'fix3.geojson'})['OUTPUT']
            QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)

        processing.run("gdal:convertformat", {'INPUT':layer_id,'OPTIONS':dsco,'OUTPUT':output})

        # verwijderen temp layers
        QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
        try:QgsProject.instance().removeMapLayer(reproject_layer.id())
        except:pass
        try:QgsProject.instance().removeMapLayer(fix)
        except:pass
        try:QgsProject.instance().removeMapLayer(dissolve)
        except:pass
        try:QgsProject.instance().removeMapLayer(snap)
        except:pass
        try:QgsProject.instance().removeMapLayer(output)
        except:pass
        
        # zet current terug
        os.chdir(cwd_before)

    def file_path(self, relative_path):
        folder = os.path.dirname(os.path.abspath(__file__))
        path_parts = relative_path.split("/")
        new_path = os.path.join(folder, *path_parts)
        return new_path
    
    def transform(self):
        """ Transform to xml """
        
        # get xslt file names
        file = self.xslt_file('GML')
        
        # fill xml for transformation from dialog
        dlg_xml = self.xml()
        
        # prepare transformation for gml creation
        QgsMessageLog.logMessage('xslt file: {}'.format(file), 'DSO GML', Qgis.Info)
        xslt = ET.parse(file)
        transform = ET.XSLT(xslt)
        
        # create gml
        output = dlg_xml.find('bestandsnaam').text
        try:
            dom = transform(dlg_xml)
            dom.write(output, encoding="utf-8", method="xml", pretty_print=True, xml_declaration=True, with_tail=None, standalone=None, compression=0)
        except:
            QgsMessageLog.logMessage("Transform failed", 'DSO GML', Qgis.Info)
            pass
        
        # create hash and add to xml for dialog
        hasher = hashlib.sha512()
        with open(output, 'rb') as afile:
            buf = afile.read()
            hasher.update(buf)

        hash = ET.SubElement(dlg_xml, 'hash')
        hash.text = hasher.hexdigest()
        
        # create xml
        file = self.xslt_file('XML')
        xslt = ET.parse(file)
        transform = ET.XSLT(xslt)

        output = output.replace('.gml','.xml')
        try:
            dom = transform(dlg_xml)
            dom.write(output, encoding="utf-8", method="xml", pretty_print=True, xml_declaration=True, with_tail=None, standalone=None, compression=0)        
        except:
            QgsMessageLog.logMessage("Transform failed", 'DSO GML', Qgis.Info)
            pass
            
    def xml(self):
        """Build xml for xslt transformation"""

        gio=ET.Element('gio')
        
        ET.SubElement(gio, 'bestandsnaam').text = self.dlg.mQgsFileWidget.filePath().replace('\\','/')
        ET.SubElement(gio, 'FRBRExpression').text = self.dlg.FRBRExpression.text()
        ET.SubElement(gio, 'soortWork').text = '/join/id/stop/work_010' #self.dlg.soortWork.text()
        ET.SubElement(gio, 'geboorteregeling').text = self.dlg.Geboorteregeling.text()
        ET.SubElement(gio, 'eindverantwoordelijke').text = self.dlg.Eindverantwoordelijke.text()
        ET.SubElement(gio, 'maker').text = self.dlg.Maker.text()
        ET.SubElement(gio, 'officieleTitel').text = self.dlg.OfficieleTitel.text()
        ET.SubElement(gio, 'alternatieveTitel').text = self.dlg.Alt_titel.text()
        ET.SubElement(gio, 'opvolgerVan').text = self.dlg.OpvolgerVan.text()
        ET.SubElement(gio, 'publicatieinstructie').text = 'TeConsolideren'
        ET.SubElement(gio, 'formaatInformatieobject').text = '/join/id/stop/informatieobject/gio_002'
        ET.SubElement(gio, 'naamInformatieObject').text = self.dlg.Naam.text()
        ET.SubElement(gio, 'id').text = str(uuid.uuid4())
        ET.SubElement(gio, 'Verwijzing').text = self.dlg.Verwijzing.text()
        ET.SubElement(gio, 'Actualiteit').text = self.dlg.Actualiteit.text()

        #ET.ElementTree(gio).write("F:/DSO/Geonovum/QGIS_plugin/gio1.xml")
        
        return gio
                
    def dso_versions(self):
        # fill dropdownlijst with versions from xslt files
        # xslt files: to_GIO-GML_<version in 5 characters>.xslt
        if self.dlg.Versie.count() == 0:
            QgsMessageLog.logMessage('Dir: {}'.format(self.plugin_dir),'DSO GML',Qgis.Info)
            dir = self.plugin_dir
            files = glob.glob('{}/to_GIO-GML_*.xsl'.format(dir))
            list = [os.path.split(x)[1][11:16] for x in files]
            self.dlg.Versie.addItems(list)
            
    def xslt_file(self, type):
        """ create xslt file name from version """
        version = self.dlg.Versie.currentText()
        file = '{0}/to_GIO-{1}_{2}.xsl'.format(self.plugin_dir, type, version)
        QgsMessageLog.logMessage('xslt file: {}'.format(file),'DSO GML',Qgis.Info)
        return file
        
    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = dsoGMLDialog()
        
        # fill name with layername in maplayercombobox
        self.setNaam()
        self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.setNaam)

        # fill version combobox
        self.dso_versions()
        
        # set the file widget
        self.dlg.mQgsFileWidget.setStorageMode(3)
        self.dlg.mQgsFileWidget.setFilter('*.gml')
        
        # set the projection widget
        self.dlg.mQgsProjectionSelectionWidget.setCrs(QgsCoordinateReferenceSystem('EPSG:28992'))
        
        #set the Actualiteit on the current date
        self.dlg.Actualiteit.setDate(date.today())
        
        # filter the layer widget (in version 3.14 the VectorTileLayer is introduced)
        try:
            self.dlg.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer|QgsMapLayerProxyModel.PluginLayer|QgsMapLayerProxyModel.PointLayer|QgsMapLayerProxyModel.PolygonLayer|QgsMapLayerProxyModel.VectorLayer|QgsMapLayerProxyModel.VectorTileLayer|QgsMapLayerProxyModel.WritableLayer)
        except:
            self.dlg.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer|QgsMapLayerProxyModel.PluginLayer|QgsMapLayerProxyModel.PointLayer|QgsMapLayerProxyModel.PolygonLayer|QgsMapLayerProxyModel.VectorLayer|QgsMapLayerProxyModel.WritableLayer)

        # auto fill if attributes exists
        self.autoFill()
        self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.autoFill)
        
        # fill attribute list
        self.fillAttributeList()
        self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.fillAttributeList)
        
        # fill attribute value list
        self.fillValueList()
        self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.fillValueList)
        self.dlg.atribuutlijst.currentTextChanged.connect(self.fillValueList)
        
        # connect change atribuutwaardelijst with 'Naam'
        self.dlg.atribuutwaardelijst.currentTextChanged.connect(self.setLocatie)

        # fill version combobox
        self.dso_versions()
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # check for a filepath
            if self.dlg.mQgsFileWidget.filePath():
                # check for filter and no value selected
                if self.dlg.Filter.isChecked() and self.dlg.atribuutwaardelijst.currentText() == '':
                    fileName = self.dlg.mQgsFileWidget.filePath()
                    FRBRExpression = self.dlg.FRBRExpression.text()
                    FRBRList = FRBRExpression.split('/')
                    item6 = FRBRList[6]
                    number = 1
                    # loop entries in attribuurwaardelijst to make GIO for each value
                    for i in range(1,self.dlg.atribuutwaardelijst.count()):
                        self.dlg.atribuutwaardelijst.setCurrentIndex(i)
                        # set filename
                        self.dlg.mQgsFileWidget.setFilePath(fileName.replace('.gml','_{}.gml'.format(self.dlg.atribuutwaardelijst.currentText())))
                        # check if FRBRExpression has placeholder <Naam>
                        if item6 == '<Naam>':
                            # use placeholder <Naam>
                            # replace 6th item in the list by value in dialog field 'Naam'
                            
                            FRBRList[6] = self.dlg.Naam.text()
                        else:
                            # use number
                            # add a _ and number to the 6th item in the list
                            #item6 = '{0}_{1}'.format(item6, number)
                            FRBRList[6] = '{0}_{1}'.format(item6, number)
                            number += 1

                        # create new FRBRExpression
                        self.dlg.FRBRExpression.setText('/'.join(FRBRList))
                        
                        self.export_dso_gml()
                        self.transform()
                        
                    self.dlg.mQgsFileWidget.setFilePath(fileName)
                else:
                    self.export_dso_gml()
                    self.transform()
                
