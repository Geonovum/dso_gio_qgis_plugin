# -*- coding: utf-8 -*-
"""
/***************************************************************************

                              DSO QGIS plugin
                              version 1.1
                              2022-02-01
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
from qgis.core import *
from qgis.gui import QgsMessageBar

from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QDate, Qt, QEvent
from PyQt5.QtWidgets import QMessageBox, QAction, QProgressBar, QDialogButtonBox
from PyQt5.QtGui import QCloseEvent, QIcon

# Initialize Qt resources from file resources.py
from .resources import *

# Import the code for the dialog
from .dso_gml_dialog import dsoGMLDialog

# xslt support
import lxml.etree as ET

import processing

import os
import tempfile
import glob
from datetime import date
import re
import uuid
import hashlib
import win32api

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
            new = self.dlg.mMapLayerComboBox.currentLayer().name().replace(' ','_')
            dir = os.path.dirname(self.dlg.mQgsFileWidget.filePath())
            if dir == '':
                dir = os.getcwd()
            #QgsMessageLog.logMessage('Nieuwe naam: {}'.format(new), 'DSO GML', Qgis.Info)
            self.dlg.Naam.setText(new)
            self.dlg.mQgsFileWidget.setFilePath('{0}\\{1}.gml'.format(dir,new))
        except:pass
        
    def setOffTitel(self):
        self.dlg.OfficieleTitel.setText('/'.join(self.dlg.FRBRExpression.text().split('/')[0:7]))
        
    def setLocatie(self):
        if self.dlg.attribuutwaardelijst.currentText() != '':
            self.dlg.Naam.setText(self.dlg.attribuutwaardelijst.currentText())

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
        #QgsMessageLog.logMessage('default: {0}/{1}/{2}'.format(lineEdit,name,default), 'DSO GML', Qgis.Info)
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
        self.dlg.attribuutlijst.clear()
        self.dlg.attribuutwaardelijst.clear()
        try:
            self.dlg.attribuutlijst.addItems(layer.fields().names())
        except:
            pass
        
    def fillValueList(self):
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        attribute = self.dlg.attribuutlijst.currentIndex()
        id = self.dlg.attribuutlijst.currentIndex()
        self.dlg.attribuutwaardelijst.clear()
        try:
            self.dlg.attribuutwaardelijst.addItem('')
            self.dlg.attribuutwaardelijst.addItems(layer.uniqueValues(id,-1))
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
        fullPath = self.dlg.mQgsFileWidget.filePath()
        folder = win32api.GetShortPathName(os.path.dirname(fullPath))
        # only allow letters, numbers, underscore and dots in filename:
        # replace all others with underscore 
        filename = re.sub('[^a-zA-Z0-9_.]', '_', os.path.basename(fullPath))
        
        output = os.path.join(folder,filename).replace('\\','/')
        
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        layer_id = layer.id()
        layer_crs = layer.crs().authid()
        target_srs = self.dlg.projectie.crs()
        QgsMessageLog.logMessage('layer_id: {}'.format(layer_id), 'DSO GML', Qgis.Info)
        # create temp dir
        temp_dir = tempfile.mkdtemp('_dso-gml')
        # save last current dir
        cwd_before = os.getcwd()
        # set temp dir as current
        os.chdir(temp_dir)
        
        # opties voor opslaan instellen
        option_target_ns = '-dsco target_namespace="https://standaarden.overheid.nl/stop/imop/geo"'
        option_prefix = '-dsco prefix=geo'
        option_xsischema = '-dsco XSISCHEMA=OFF'
        option_xsischemauri = '-dsco XSISCHEMAURI="http://www.w3.org/2001/XMLSchema-instance"'
        option_format = '-dsco FORMAT="GML3.2"'
        option_gml_feature_collection = '-dsco GML_FEATURE_COLLECTION=no'
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
            
        #QgsMessageLog.logMessage('layer id: {}'.format(layer_id), 'DSO GML', Qgis.Info)
        
        dsco = ' '.join([option_target_ns,
                         option_prefix,
                         option_xsischema,
                         option_xsischemauri,
                         option_format,
                         option_gml_feature_collection,
                         option_write_feature_bounded_by,
                         nln,
                         nlt])
                         
        #QgsMessageLog.logMessage(dsco, 'DSO GML', Qgis.Info)
        
        # select features if attribuutlijst en attribuutwaardelijst is activated
        QgsMessageLog.logMessage('Dissolve: {}'.format(str(self.dlg.dissolve.isChecked())), 'DSO GML', Qgis.Info)
        field=''
        if self.dlg.Filter.isChecked() == 1:
            if self.dlg.attribuutwaardelijst.currentText()=='':
                field = self.dlg.attribuutlijst.currentText()
            elif not (self.dlg.dissolve.checkState() == 0 and self.dlg.Losse_GIOs.isChecked()):
                layer.selectByExpression("\"{0}\"=\'{1}\'".format(self.dlg.attribuutlijst.currentText(),self.dlg.attribuutwaardelijst.currentText()))
        
        # select all features if no features are selected
        if layer.selectedFeatureCount() == 0:
            layer.selectAll()
        
        # extract selected features
        # QgsProcessingParameterVectorLayer
        layer_id=extracted=processing.run("native:saveselectedfeatures", {'INPUT':layer_id,'OUTPUT':'extracted.geojson'})['OUTPUT']
        
        # get layer and make valid
        if self.dlg.valide.checkState() == 2:
            try:QgsProject.instance().removeMapLayer(fix)
            except:pass
            layer_id=fix=processing.run("native:fixgeometries", {'INPUT':layer_id,'OUTPUT':'fix.geojson'})['OUTPUT']
            #layer_id=fix=processing.run("native:fixgeometries", {'INPUT':QgsProcessingFeatureSourceDefinition(layer_id, selectedFeaturesOnly=True, featureLimit=-1, geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),'OUTPUT':'fix.geojson'})['OUTPUT']
            
        # Dissolvwe
        if self.dlg.dissolve.checkState() == 2:
            if field:
                layer_id=dissolve=processing.run("native:dissolve", {'INPUT':layer_id,'FIELD':[field],'OUTPUT':'dissolve.geojson'})['OUTPUT']
            else:
                layer_id=dissolve=processing.run("native:dissolve", {'INPUT':layer_id,'FIELD':[],'OUTPUT':'dissolve.geojson'})['OUTPUT']
            #processing.run("native:dissolve", {'INPUT':'F:\\DSO\\Geonovum\\GitHub\\xml_omgevingsplan_gemeentestad\\opdracht\\Bouwhoogte.gml|layername=gio|geometrytype=Polygon|option:FORCE_SRS_DETECTION=YES','FIELD':['kwantitatieveNormwaarde'],'OUTPUT':'TEMPORARY_OUTPUT'})
        
        # Simplify Distance (Douglas-Peucker)
        if self.dlg.simplify.checkState() == 2:
            # get the numer for afstand: from mm to m
            meter = self.dlg.afstand.value()/1000
            layer_id=simplify=processing.run("native:simplifygeometries", {'INPUT':layer_id,'METHOD':0,'TOLERANCE':meter,'OUTPUT':'simplify.geojson'})['OUTPUT']
        
        # Snap - valid
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
                #QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
                try:QgsProject.instance().removeMapLayer(fix)
                except:pass
                layer_id = fix = processing.run("native:fixgeometries", {'INPUT':layer_id,'OUTPUT':'fix2.geojson'})['OUTPUT']
                #QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
                test = processing.run("qgis:checkvalidity", {'INPUT_LAYER':layer_id,'METHOD':2,'IGNORE_RING_SELF_INTERSECTION':False})['ERROR_COUNT']
                #QgsMessageLog.logMessage('test: {}'.format(test), 'DSO GML', Qgis.Info)
            
        if self.dlg.valide.checkState() == 2:
            try:QgsProject.instance().removeMapLayer(fix)
            except:pass
            layer_id = fix = processing.run("native:fixgeometries", {'INPUT':layer_id,'OUTPUT':'fix3.geojson'})['OUTPUT']
        
        QgsMessageLog.logMessage('Export: {}'.format(output), 'DSO GML', Qgis.Info)
        processing.run("gdal:convertformat", {'INPUT':layer_id,'OPTIONS':dsco,'OUTPUT':output})

        # verwijderen temp layers
        #QgsMessageLog.logMessage('lagen: {}'.format([layer.name() for layer in QgsProject.instance().mapLayers().values()]), 'DSO GML', Qgis.Info)
        try:QgsProject.instance().removeMapLayer(reproject_layer.id())
        except:pass
        try:QgsProject.instance().removeMapLayer(extracted)
        except:pass
        try:QgsProject.instance().removeMapLayer(fix)
        except:pass
        try:QgsProject.instance().removeMapLayer(simplify)
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
        #return
        # prepare transformation for gml creation
        QgsMessageLog.logMessage('xslt file: {}'.format(file), 'DSO GML', Qgis.Info)
        xslt = ET.parse(file)
        transform = ET.XSLT(xslt)
        
        # create gml
        output = dlg_xml.find('bestandsnaam').text.replace('\\','/')
        QgsMessageLog.logMessage('Output file: {}'.format(output), 'DSO GML', Qgis.Info)
        try:
            dom = transform(dlg_xml)
            dom.write(output, encoding="utf-8", method="xml", pretty_print=True, xml_declaration=True, with_tail=None, standalone=None, compression=0)
        except Exception as err:
            for xsl_error in transform.error_log:
                QgsMessageLog.logMessage('XSLTError: {}'.format(xsl_error), 'DSO GML', Qgis.Info)
            msg = QMessageBox()
            msg.setText("Transform failed")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            self.iface.messageBar().pushMessage("Critical", "Transform failed", level=Qgis.Critical, duration=20)
            QgsMessageLog.logMessage("Transformation failed", 'DSO GML', Qgis.Critical)
            self.dlg.reject()
        
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
            for xsl_error in transform.error_log:
                QgsMessageLog.logMessage('XSLTError: {}'.format(xsl_error), 'DSO GML', Qgis.Info)
            msg = QMessageBox()
            msg.setText("Transform failed")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            self.iface.messageBar().pushMessage("Critical", "Transform failed", level=Qgis.Critical, duration=20)
            QgsMessageLog.logMessage("Transformation failed", 'DSO GML', Qgis.Critical)
            self.dlg.reject()
            
    def xml(self):
        """Build xml for xslt transformation"""

        gio=ET.Element('gio')
        fullPath = self.dlg.mQgsFileWidget.filePath()
        folder = win32api.GetShortPathName(os.path.dirname(fullPath))
        # only allow letters, numbers, underscore and dots in filename:
        # replace all others with underscore 
        filename = re.sub('[^a-zA-Z0-9_.]', '_', os.path.basename(fullPath))
        ET.SubElement(gio, 'bestandsnaam').text = os.path.join(folder,filename).replace('\\','/')
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
        ET.SubElement(gio, 'Verwijzing').text = self.dlg.Verwijzing.text()
        ET.SubElement(gio, 'Actualiteit').text = self.dlg.Actualiteit.text()
        ET.SubElement(gio, 'naamInformatieObject').text = self.dlg.Naam.text()
        ET.SubElement(gio, 'id').text = str(uuid.uuid4())
        # add enough guids and names for use with multiple locations
        ids = ET.SubElement(gio, 'ids')
        names = ET.SubElement(gio, 'namen')
        layer = self.dlg.mMapLayerComboBox.currentLayer()
        features = []
        for feature in layer.getFeatures():
            ET.SubElement(ids, 'id').text = str(uuid.uuid4())
            # create names with values
            ET.SubElement(names, 'naamInformatieObject').text = '{0}-{1}'.format(self.dlg.Naam.text(),str(feature.id()))
        # get selected attribute when filter is checked
        if self.dlg.Filter.isChecked():
            ET.SubElement(gio, 'Attribuut').text = self.dlg.attribuutlijst.currentText()
        else:
            ET.SubElement(gio, 'Attribuut').text = ''
        # Uncomment next line and change path for debugging
        # ET.ElementTree(gio).write("C:/Users/W10_admin/Documents/gio.xml")
        return gio
                
    def dso_versions(self):
        # fill dropdownlijst with versions from xslt files in plugin directory
        # xslt files: (to_GIO-GML_1.1.0.xsl)
        if self.dlg.Versie.count() == 0:
            dir = self.plugin_dir.replace('\\','/')
            files = glob.glob('{}/to_GIO-GML_*.xsl'.format(dir))
            list = ['.'.join(os.path.split(x)[1].split('_')[2].split('.')[0:3]) for x in files]
            self.dlg.Versie.addItems(list)
            self.dlg.Versie.setCurrentIndex(len(list)-1)
            
    def xslt_file(self, type):
        """ create xslt file name from version """
        version = self.dlg.Versie.currentText()
        file = '{0}/to_GIO-{1}_{2}.xsl'.format(self.plugin_dir.replace('\\','/'), type, version)
        return file
        
    def result_check(self):
        # checks on input data
        result=[]
        if not self.dlg.mQgsFileWidget.filePath():
            result.append("Geen gml bestand gekozen")
        # FRBRExpression checks
        # BG('gm', 'mnre' or 'ws' with 4 digits. 'pv' with 2 digits)
        bg_p = re.compile('\\b(gm|mnre|ws)([0-9]{4})\\b|\\b(pv)([0-9]{2})\\b')
        FRBRExpression = self.dlg.FRBRExpression.text()
        if not FRBRExpression:
            # FRBRExpression is empty
            result.append("Geen FRBRExpression opgegeven")
        elif not FRBRExpression[:17] == '/join/id/regdata/':
            result.append("FRBRExpression is geen geldige join identifier")
        elif len(FRBRExpression.split('/')) < 8:
            result.append("FRBRExpression is niet volledig")
        elif len(FRBRExpression.split(' '))>1:
            result.append("FRBRExpression bevat een spatie")
        elif len(FRBRExpression.split('.'))>1:
            result.append("FRBRExpression bevat een punt")
        elif not bg_p.match(FRBRExpression.split('/')[4]):
            result.append("Fout in BG deel van FRBRExpression")
        return result
        
    def create_GIO(self, button):
        button_text = button.text()
        #QgsMessageLog.logMessage('Button {0} '.format(button_text),'DSO GML', Qgis.Warning)
        # check for Ok or Apply button click
        button_list = ['OK','Apply']
        if button_text in button_list:
            #Do checks
            check = self.result_check()
            # if no checks then proceed
            if not check:
                # get layer, layer id, filename and FFRBRExpression (original)
                layer = self.dlg.mMapLayerComboBox.currentLayer()
                layer_id = layer.id()
                fileName = self.dlg.mQgsFileWidget.filePath()
                FRBRExpression = self.dlg.FRBRExpression.text()
                Locatie_Naam = self.dlg.Naam.text()
                # split the expression
                FRBRList = FRBRExpression.split('/')
                # get the <overig> part of the expression
                item6 = FRBRList[6]
                # check if there are features selected and filter is checked
                featCount = layer.selectedFeatureCount()
                if featCount:
                    if self.dlg.Filter.isChecked():
                        msg = QMessageBox(windowTitle='Geselecteerde features')
                        msg.setText('Er {0} {1} feature{2} (locatie{2}) geselecteerd.\r\nBij gebruik van een filter wordt deze selectie genegeerd.'.format(('is' if featCount==1 else 'zijn'),str(featCount),('' if featCount==1 else 's')))
                        msg.setInformativeText('Doorgaan (Ok) of sluiten (Cancel)?')
                        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
                        msg.setIcon(QMessageBox.Warning)
                        msg.setDefaultButton(QMessageBox.Ok)
                        msg_response = msg.exec_()
                        if msg_response == QMessageBox.Cancel:
                            QgsMessageLog.logMessage('Er {0} {1} feature{2} (locatie{2}) geselecteerd, actie afgebroken.'.format(('is' if featCount==1 else 'zijn'),str(featCount),('' if featCount==1 else 's')),'DSO GML', Qgis.Info)
                            return
                    # save selected feature ids
                    original_ids = layer.selectedFeatureIds()
                # check if more than 1 GIO needs to be made
                # dissolve /Losse_GIOs /Filter /attribuut
                if (self.dlg.dissolve.checkState() == 2 and self.dlg.Losse_GIOs.isChecked() and self.dlg.Filter.isChecked() and not self.dlg.attribuutlijst.currentText()=='' and self.dlg.attribuutwaardelijst.currentText()==''):
                    QgsMessageLog.logMessage('Meerdere GIO''s voor elke waarde 1 met features samengesmolten tot 1 Locatie','DSO GML', Qgis.Info)
                    # save ids of currrent selection
                    # get initial filename and item 6 from FRBRExpression
                    number = 1
                    # loop entries in attribuurwaardelijst to make GIO for each value
                    for i in range(1,self.dlg.attribuutwaardelijst.count()):
                        self.dlg.attribuutwaardelijst.setCurrentIndex(i)
                        
                        # set filename
                        self.dlg.mQgsFileWidget.setFilePath(fileName.replace('.gml','_{}.gml'.format(self.dlg.attribuutwaardelijst.currentText())))
                        
                        # cat expression with Naam or number
                        self.catExpression(FRBRList, item6, number)
                        number += 1
                        
                        self.export_dso_gml()
                        self.transform()
                    self.dlg.attribuutwaardelijst.setCurrentIndex(0)
                elif (self.dlg.dissolve.checkState() == 0 and self.dlg.Losse_GIOs.isChecked()):
                    QgsMessageLog.logMessage('Meerdere GIO''s/ {}'.format('Filter aan' if str(self.dlg.Filter.isChecked()) else 'Filter uit'),'DSO GML', Qgis.Info)
                    # if Filter is unchecked
                    QgsMessageLog.logMessage('Laag: {}'.format(str(layer_id)),'DSO GML', Qgis.Info)
                    
                    if not self.dlg.Filter.isChecked():
                        QgsMessageLog.logMessage('Geen filter','DSO GML', Qgis.Info)
                        # loop through all features
                        for feat in layer.getFeatures():
                            # prepare filename and FBRExpression
                            # set filename
                            self.dlg.mQgsFileWidget.setFilePath(fileName.replace('.gml','_{}.gml'.format(feat.id())))
                            
                            # catExpression with Naam or number
                            self.catExpression(FRBRList, item6, feat.id())
                            
                            layer.select(feat.id())
                            self.export_dso_gml()
                            self.transform()
                            layer.deselect(feat.id())
                    else:
                        QgsMessageLog.logMessage('attribuutwaarde {}'.format(self.dlg.attribuutwaardelijst.currentText()),'DSO GML', Qgis.Info)
                        number = 1
                        if self.dlg.attribuutwaardelijst.currentText()=='':
                            QgsMessageLog.logMessage('Filter en geen attribuutwaarde, attribuut: {}'.format(self.dlg.attribuutlijst.currentText()),'DSO GML', Qgis.Info)
                            # group all features on attribuutwaarde and loop through groups
                            attribuut = self.dlg.attribuutlijst.currentText()
                            idx = layer.fields().indexOf(attribuut)
                            attribuutwaarden =  layer.uniqueValues(idx)
                            for waarde in attribuutwaarden:
                                QgsMessageLog.logMessage('Attribuutwaarde: {}'.format(waarde),'DSO GML', Qgis.Info)
                                layer.selectByExpression("\"{0}\"=\'{1}\'".format(attribuut,waarde))
                                QgsMessageLog.logMessage('Selectie: {}'.format(str(layer.selectedFeatureCount())),'DSO GML', Qgis.Info)
                                # set value in Naam
                                self.dlg.Naam.setText(waarde)
                                self.dlg.mQgsFileWidget.setFilePath(fileName.replace('.gml','_{0}-{1}.gml'.format(attribuut.replace(' ','_'),waarde.replace(' ','_'))).replace('\\','/'))
                                
                                self.catExpression(FRBRList, item6, number)
                                number +=1
                                
                                self.export_dso_gml()
                                self.transform()
                        else:
                            QgsMessageLog.logMessage('Filter en attribuutwaarde','DSO GML', Qgis.Info)
                            attribuut = self.dlg.attribuutlijst.currentText()
                            waarde = self.dlg.attribuutwaardelijst.currentText()
                            # loop through filtered features
                            layer.selectByExpression("\"{0}\"=\'{1}\'".format(attribuut,waarde))
                            feats = layer.selectedFeatureIds()
                            layer.removeSelection()
                            for fid in feats:
                                layer.selectByIds([fid])
                                QgsMessageLog.logMessage('fid: {}'.format(fid),'DSO GML', Qgis.Info)
                                QgsMessageLog.logMessage('FeatureCount: {}'.format(str(layer.selectedFeatureCount())),'DSO GML', Qgis.Info)
                                self.dlg.mQgsFileWidget.setFilePath(fileName.replace('.gml','_{0}-{1}-{2}.gml'.format(attribuut.replace(' ','_'),waarde.replace(' ','_'),str(fid))).replace('\\','/'))
                                # catExpression with Naam or number
                                self.catExpression(FRBRList, item6, fid)
                                self.export_dso_gml()
                                self.transform()
                                layer.removeSelection()
                else:
                    QgsMessageLog.logMessage('1 GIO','DSO GML', Qgis.Info)
                    self.catExpression(FRBRList, item6)
                    self.export_dso_gml()
                    self.transform()
                # clear selection
                layer.removeSelection()
                # set original selection
                if featCount:
                    layer.selectByIds(original_ids)
                # set original filename and FRBRExpression
                self.dlg.mQgsFileWidget.setFilePath(fileName)
                self.dlg.FRBRExpression.setText(FRBRExpression)
                # set original Locatie Naam
                self.dlg.Naam.setText(Locatie_Naam)
                # With Apply keep dialog open
                if button_text == 'Apply':
                    self.run()
                    return
                self.iface.messageBar().pushMessage("Transformatie","Gereed", level=Qgis.MessageLevel.Info, duration=20)
            else:
                QgsMessageLog.logMessage('Invoerfouten:\n{}'.format('\n'.join(check)),'DSO GML', Qgis.Critical)
                self.iface.messageBar().pushMessage("Invoer controle", "Fouten gevonden",'\n'.join(check), level=Qgis.Critical, duration=20)
    
    def catExpression(self, FRBRList, item6, number=0):
        # cat the FRBRExpression for multiple file export
        # if FRBRExpression has placeholder <Naam> use Naam
        if item6 == '<Naam>':
            # use placeholder <Naam>: replace 6th item in the list by value in dialog field 'Naam'
            FRBRList[6] = self.dlg.Naam.text().replace(' ','_')
        elif number > 0:
            # use number: add a _ and number to the 6th item in the list
            FRBRList[6] = '{0}_{1}'.format(item6, number)
        # create new FRBRExpression
        self.dlg.FRBRExpression.setText('/'.join(FRBRList))
        
    def run(self):
        """Run method that performs all the real work"""
        
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = dsoGMLDialog()
            # set only first time onnections
            self.dlg.button_box.clicked.connect(self.create_GIO)
            # fill version combobox
            self.dso_versions()
            #fill OfficieleTitle wit FRBRExpression
            self.dlg.FRBRExpression.textChanged.connect(self.setOffTitel)
            # set the file widget
            self.dlg.mQgsFileWidget.setStorageMode(3)
            self.dlg.mQgsFileWidget.setFilter('*.gml')
            # set the projection widget
            self.dlg.projectie.setCrs(QgsCoordinateReferenceSystem('EPSG:28992'))
            #set the Actualiteit on the current date
            self.dlg.Actualiteit.setDate(date.today())
            # filter the layer widget (in version 3.14 the VectorTileLayer is introduced)
            try:
                self.dlg.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer|QgsMapLayerProxyModel.PluginLayer|QgsMapLayerProxyModel.PointLayer|QgsMapLayerProxyModel.PolygonLayer|QgsMapLayerProxyModel.VectorLayer|QgsMapLayerProxyModel.VectorTileLayer|QgsMapLayerProxyModel.WritableLayer)
            except:
                self.dlg.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer|QgsMapLayerProxyModel.PluginLayer|QgsMapLayerProxyModel.PointLayer|QgsMapLayerProxyModel.PolygonLayer|QgsMapLayerProxyModel.VectorLayer|QgsMapLayerProxyModel.WritableLayer)
            # auto fill if attributes exists
            #self.autoFill()
            #self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.autoFill)
            # fill attribute list
            self.fillAttributeList()
            self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.fillAttributeList)
            # fill attribute value list
            self.fillValueList()
            self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.fillValueList)
            self.dlg.attribuutlijst.currentTextChanged.connect(self.fillValueList)
            # connect change attribuutwaardelijst with 'Naam'
            self.dlg.attribuutwaardelijst.currentTextChanged.connect(self.setLocatie)
            # fill name with layername in maplayercombobox
            self.dlg.mMapLayerComboBox.currentTextChanged.connect(self.setNaam)
            self.setNaam()
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        self.dlg.exec_()
