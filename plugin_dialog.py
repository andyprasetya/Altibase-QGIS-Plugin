# -*- coding: utf-8 -*-
"""
/***************************************************************************
 AltibasePluginDialog
                                 A QGIS plugin
 This plugin allows Altibase vector layer.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2020-06-29
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Altibase Corp.
        email                : us@altibase.com
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

import os
import sys
import binascii

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from PyQt5.QtWidgets import *
from PyQt5.Qt import QStandardItemModel, QStandardItem, QTableWidgetItem
from qgis.core import *
from .conn_dialog import *
from qgis.utils import iface

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'plugin_dialog_base.ui'))


class AltibasePluginDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AltibasePluginDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.g_conn_name = None
        self.g_layers = []
        self.g_layers_info = []

        '''
        # layer별 쿼리모음
        self.g_layer_querys =
        [
            {layerID:1, querys:query_dic_list_1},
            {layerID:2, querys:query_dic_list_2},
            ...
        ]
        # fid별 query
        query_dic_list_1 =
        [
            {fid:1, query:update ...},
            {fid:2, query:delete ...},
            ...
        ]
        '''
        self.g_layer_querys = []

        self.g_layers_added_features_dic = {}
        self.g_layers_removed_features_dic = {}
        self.g_layers_removed_features_pk_dic = {}

        self.g_layers_error_dic = {}
        self.g_layers_invalid_feature_dic = {}

        self.g_msgbar = QgsMessageBar()
        self.g_msgbar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setLayout(QGridLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().addWidget(self.g_msgbar, 0, 0, 1, 1)
        self.layout().setAlignment(Qt.AlignTop)

        self.g_alti_conn = AltiConn()
        self.g_new_conndlg = AltibaseConnectionDialog()
        self.g_edit_conndlg = AltibaseConnectionDialog()

        self.LayerList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.AttrList.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ConnectBt.clicked.connect(self.ConnectBtFunc)
        self.NewBt.clicked.connect(self.NewBtFunc)
        self.EditBt.clicked.connect(self.EditBtFunc)
        self.RemoveBt.clicked.connect(self.RemoveBtFunc)
        self.RefreshBt.clicked.connect(self.RefreshBtFunc)
        self.AddBt.clicked.connect(self.AddBtFunc)
        self.CloseBt.clicked.connect(self.CloseBtFunc)
        self.LayerList.itemSelectionChanged.connect(self.getAttrTable)
        self.LayerList.itemDoubleClicked.connect(self.addLayer)
        self.First100RBt.clicked.connect(self.getAttrTable)
        self.AllRowsRBt.clicked.connect(self.getAttrTable)
        self.g_new_conndlg.g_close_signal.connect(self.addItem)
        self.g_edit_conndlg.g_close_signal.connect(self.addItem2)

    def dlgClear(self):
        self.LayerList.itemSelectionChanged.disconnect()
        self.LayerList.setRowCount(0)
        self.LayerList.itemSelectionChanged.connect(self.getAttrTable)
        self.AttrList.setRowCount(0)
        self.AttrList.setColumnCount(0)
        self.LayerNameLabel.clear()
        self.ConnInfoLabel.clear()

    def msgbar_logging(self, type, msg):
        if type == "info":
            self.g_msgbar.pushMessage(msg, level=Qgis.Info, duration=2)
        else:
            widget = self.g_msgbar.createMessage("Error", "{0}".format(msg))
            button = QPushButton(widget)
            button.setText("View message log")
            widget.layout().addWidget(button)
            self.g_msgbar.pushWidget(widget, Qgis.Warning)
                
    def ConnectBtFunc(self):
        self.g_msgbar.clearWidgets()
        conn_name = self.ConnComboBox.currentText()
        if not conn_name:
            QMessageBox.warning(self,
                                "Error",
                                "Connection Name is required.",
                                QMessageBox.Ok)
            return

        self.dlgClear()

        res = self.g_alti_conn.connectDB(conn_name)
        if not res:
            self.msgbar_logging("info", "Connection successful")
            self.ConnInfoLabel.setText(conn_name)
            self.getLayerList()
        else:
            self.msgbar_logging("warning", res)

    def getLayerList(self):
        s_rows = self.g_alti_conn.execSelect("select count(*) from geometry_columns")
        if not s_rows or s_rows[0][0] == 0:
            QMessageBox.warning(self,
                                "Error",
                                "There is no tables with geometry",
                                QMessageBox.Ok)
            return

        s_rows = self.g_alti_conn.execSelect("select F_TABLE_SCHEMA, F_TABLE_NAME, F_GEOMETRY_COLUMN, COORD_DIMENSION, SRID \
                                              from geometry_columns")
        for s_row_num, s_row in enumerate(s_rows):
            self.LayerList.insertRow(s_row_num)
            for s_col_num, s_col in enumerate(s_row):
                self.LayerList.setItem(s_row_num, s_col_num, QTableWidgetItem(str(s_col)))

        self.LayerList.resizeColumnsToContents()
        self.LayerList.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def NewBtFunc(self):
        self.g_new_conndlg.g_msgbar.clearWidgets()
        self.g_new_conndlg.clear("new")
        # show the dialog
        self.g_new_conndlg.show()
        # Run the dialog event loop
        s_result = self.g_new_conndlg.exec_()
        # See if OK was pressed
        if s_result:
            pass

    def EditBtFunc(self):
        self.g_conn_name = self.ConnComboBox.currentText()
        if not self.g_conn_name: return

        self.g_edit_conndlg.g_msgbar.clearWidgets()
        self.g_edit_conndlg.set("edit", self.g_conn_name)

        # show the dialog
        self.g_edit_conndlg.show()
        # Run the dialog event loop
        s_result = self.g_edit_conndlg.exec_()
        # See if OK was pressed
        if s_result:
            pass

    def RemoveBtFunc(self):
        self.g_msgbar.clearWidgets()
        alti_config = AltiConfig()
        alti_config.removeConfig(self.ConnComboBox.currentText())
        self.ConnComboBox.removeItem(self.ConnComboBox.currentIndex())

    def RefreshBtFunc(self):
        conn_name = self.ConnInfoLabel.text()
        self.g_msgbar.clearWidgets()
        self.dlgClear()
        self.ConnInfoLabel.setText(conn_name)
        self.getLayerList()
        item = self.LayerList.item(0,0)
        self.LayerList.scrollToItem(item)

    def AddBtFunc(self):
        self.g_msgbar.clearWidgets()
        s_selected_range_list = self.LayerList.selectedRanges()
        if s_selected_range_list == [] :
            return

        for s_selected_range in s_selected_range_list:
            for i in range(s_selected_range.rowCount()):
                s_schema = self.LayerList.item(s_selected_range.topRow()+i,0).text()
                s_table = self.LayerList.item(s_selected_range.topRow()+i,1).text()
                self.addLayer2(s_schema,s_table)
        
    def CloseBtFunc(self):
        self.close()

    def closeEvent(self, evnt):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Warning)
        msgBox.setWindowTitle('Altibase Plug-in')
        msgBox.setText("Please check whether this project includes one or more temporary scratch layers. \
                        \nThese layers are not saved to disk and their contents will be permanently lost. \
                        \nAre you sure you want to proceed?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        s_result = msgBox.exec_()
        if s_result == QMessageBox.Cancel:
            evnt.ignore()
        else:
            self.g_alti_conn.disconnectDB()
    
            for layer in self.g_layers:
                self.disconnectSignalsFromLayer(layer)
    
            self.dlgClear()
            super(AltibasePluginDialog, self).closeEvent(evnt)

    def getAttrTable(self):
        s_col_header = []
        s_col_list = []
        s_except_datatype = ['VARBIT', 'BIT', 'BLOB', 'CLOB', 'GEOMETRY', 'BYTE', 'NIBBLE', 'VARBYTE', 'BINARY', 'ECHAR', 'EVARCHAR']

        self.AttrList.clear()
        self.AttrList.setColumnCount(0)
        self.AttrList.setRowCount(0)

        s_cur_schema = self.LayerList.item(self.LayerList.currentRow(),0).text()
        s_cur_table = self.LayerList.item(self.LayerList.currentRow(),1).text()

        i=0
        s_rows = self.g_alti_conn.execColumns(s_cur_schema, s_cur_table)
        if s_rows:
            for s_row in s_rows:
                if s_row[5] not in s_except_datatype:
                    self.AttrList.insertColumn(i)
                    i += 1
                    s_col_header.append(s_row[3])
                    s_col_list.append('"' + s_row[3] + '"')
            self.AttrList.setHorizontalHeaderLabels(s_col_header)

            if self.First100RBt.isChecked():
                s_rows = self.g_alti_conn.execSelect('select %s \
                                                      from "%s"."%s" limit 100' % (",".join(s_col_list), s_cur_schema, s_cur_table))
            else:
                s_rows = self.g_alti_conn.execSelect('select %s \
                                                      from "%s"."%s"' % (",".join(s_col_list), s_cur_schema, s_cur_table))

            for s_row_num, s_row in enumerate(s_rows):
                self.AttrList.insertRow(s_row_num)
                for s_col_num, s_col in enumerate(s_row):
                    self.AttrList.setItem(s_row_num, s_col_num, QTableWidgetItem(str(s_col)))

            self.LayerList.resizeColumnsToContents()
            self.LayerNameLabel.setText(s_cur_schema + '.' + s_cur_table)
            self.AttrList.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def addLayer(self):
        s_cur_schema = self.LayerList.item(self.LayerList.currentRow(),0).text()
        s_cur_table = self.LayerList.item(self.LayerList.currentRow(),1).text()
        self.addLayer2(s_cur_schema,s_cur_table)

    def addLayer2(self, a_schema, a_table):
        uri = ""
        col_list = ""
        s_layername = a_schema + '.' + a_table
        s_features = []

        # get primary key info
        s_rows = self.g_alti_conn.execPrimaryKeys(a_schema, a_table)
        if not s_rows:
            QgsMessageLog.logMessage('Primary key is required. : %s' % a_table, 'AltibasePlugin' )
            return
        s_pk = s_rows[0][3]
        ''' index=yes 여부 결정 필요 '''
        uri = "key=" + s_pk + "&index=yes"

        # get attributes info
        ''' layer table을 select해서 attribute 세팅할때 컬럼순서가 관련 있음. '''
        s_rows = self.g_alti_conn.execColumns(a_schema, a_table)
        if not s_rows: return
        col_info = {row.column_name: row for row in s_rows}
        for key in col_info.keys():
            s_type_name = self.getFieldType(col_info.get(key).type_name)
            if s_type_name == "none": continue  # except binary type
            if s_type_name in ["double"]:
                ''' precision, scale 값이 들어가는 것이 맞는지 확인 필요.. '''
                attr_def = "field=%s:%s(%d,%d)" % (key, s_type_name, col_info.get(key).column_size, col_info.get(key).decimal_digits)
            elif s_type_name in ["string"]:
                attr_def = "field=%s:%s(%d)" % (key, s_type_name, col_info.get(key).column_size)
            else:
                attr_def = "field=%s:%s" % (key, s_type_name)
            uri = uri + "&" + attr_def

            # layer table의 select 쿼리 생성을 위한 target list를 만든다.
            if not col_list:
                col_list = '"' + key + '"'
            else:
                col_list = col_list + ", " + '"' + key + '"'

        # get geometry_type, srid info
        s_rows = self.g_alti_conn.execSelect("select a.F_GEOMETRY_COLUMN, b.AUTH_SRID, b.AUTH_NAME, a.SRID \
                                              from geometry_columns a left outer join SPATIAL_REF_SYS b on a.srid = b.srid \
                                              where F_TABLE_SCHEMA = '%s' \
                                                and F_TABLE_NAME = '%s'" % (a_schema, a_table))
        if not s_rows:
            QgsMessageLog.logMessage('%s does not exist in geometry_columns.' % a_table, 'AltibasePlugin' )
            return
        s_geom_col_name = s_rows[0][0]
        s_auth_srid = s_rows[0][1]
        s_auth_name = s_rows[0][2]
        s_srid = s_rows[0][3]
        if s_auth_name:
            uri = "crs=" + s_auth_name + ":" + str(s_auth_srid) + "&" + uri

        ''' 하나의 테이블에 한가지 이상의 geometry type이 존재하는 경우, layer 분리 '''
        s_rows = self.g_alti_conn.execSelect('select distinct GEOMETRYTYPE("%s") from "%s"."%s"' % (s_geom_col_name, a_schema, a_table))
        ''' 데이터가 0건인 경우, GEOMETRYTYPE을 알 수가 없어서 QgsVectorLayer를 만들 수 없음.
            postgis의 경우, 0건이어도 add layer가 됨 '''
        if not s_rows:
            QgsMessageLog.logMessage('Error : Fail to add layer as there is no data in layer(%s).' % a_table, 'AltibasePlugin' )
            return

        for s_row in s_rows:
            s_geom_type = s_row[0]
            s_layer_uri = s_geom_type + "?" + uri
            s_layer = QgsVectorLayer(s_layer_uri, s_layername, 'memory')
            if not s_layer.isValid():
                QgsMessageLog.logMessage('Error : Layer %s did not load.' % a_table, 'AltibasePlugin' )
                continue

            ''' fetchmany를 고려해야 할 수도 있음. '''
            s_rows = self.g_alti_conn.execSelect('select "%s", asbinary("%s"), %s from "%s"."%s" where GEOMETRYTYPE("%s")=\'%s\''
                                                 % (s_pk, s_geom_col_name, col_list, a_schema, a_table, s_geom_col_name, s_geom_type))
            if s_rows:
                for s_row in s_rows:
                    s_feature = QgsFeature()
                    s_geometry = QgsGeometry()
                    s_feature.setAttributes(list(s_row[2:]))
                    s_geometry.fromWkb(s_row[1])
                    s_feature.setGeometry(s_geometry)
                    s_features.append(s_feature)
                s_layer.dataProvider().addFeatures(s_features)

            QgsProject.instance().addMapLayer(s_layer)

            self.g_layers.append(s_layer)
            self.connectSignalsToLayer(s_layer)
            s_layerid = s_layer.id()
            self.g_layers_added_features_dic[s_layerid] = []
            self.g_layers_removed_features_dic[s_layerid] = []

            layer_info = {}
            layer_info['id'] = s_layerid
            layer_info['name'] = s_layer.name()
            layer_info['pk'] = s_pk
            layer_info['geom'] = s_geom_col_name
            layer_info['srid'] = s_srid
            layer_info['conn_name'] = self.ConnInfoLabel.text()
            self.g_layers_info.append(layer_info)

    def getFieldType(self, a_type):
        conv_type = {'CHAR': 'string', \
                    'VARCHAR': 'string', \
                    'NCHAR': 'string', \
                    'NVARCHAR': 'string', \
                    'NUMERIC': 'double', \
                    'DEDIMAL': 'double', \
                    'FLOAT': 'double', \
                    'NUMBER': 'double', \
                    'DOUBLE': 'double', \
                    'REAL': 'double', \
                    'BIGINT': 'integer', \
                    'INTEGER': 'integer', \
                    'SMALLINT': 'integer', \
                    'DATE': 'string'}
        if a_type in conv_type:
            return conv_type[a_type]
        else: return "none"

    def addItem(self):
        self.ConnComboBox.addItem(self.g_new_conndlg.getConnName())
        self.ConnComboBox.setCurrentIndex(self.ConnComboBox.count()-1)

    def addItem2(self):
        self.ConnComboBox.removeItem(self.ConnComboBox.findText(self.g_conn_name))
        self.ConnComboBox.addItem(self.g_edit_conndlg.getConnName())
        self.ConnComboBox.setCurrentIndex(self.ConnComboBox.count()-1)

    def connectSignalsToLayer(self, a_layer):
        a_layer.committedFeaturesAdded.connect(self.committedFeaturesAdded)
        a_layer.committedAttributeValuesChanges.connect(self.committedAttributeValuesChanges)
        a_layer.committedGeometriesChanges.connect(self.committedGeometriesChanges)
        a_layer.committedFeaturesRemoved.connect( self.committedFeaturesRemoved )

        a_layer.editingStarted.connect(lambda: self.editingStarted(a_layer))
        a_layer.editingStopped.connect(lambda: self.editingStopped(a_layer))

        a_layer.featureDeleted.connect(lambda featureid: self.featureDeleted(a_layer, featureid))

    def disconnectSignalsFromLayer(self, a_layer):
        try:
            a_layer.committedFeaturesAdded.disconnect(self.committedFeaturesAdded)
            a_layer.committedAttributeValuesChanges.disconnect(self.committedAttributeValuesChanges)
            a_layer.committedGeometriesChanges.disconnect(self.committedGeometriesChanges)
            a_layer.committedFeaturesRemoved.disconnect(self.committedFeaturesRemoved)

            a_layer.editingStarted.disconnect(lambda: self.editingStarted(a_layer))
            a_layer.editingStopped.disconnect(lambda: self.editingStopped(a_layer))

            a_layer.featureDeleted.disconnect(lambda featureid: self.featureDeleted(a_layer, featureid))
        except:
            pass

    def committedFeaturesAdded(self, a_layer, a_features):
        QgsMessageLog.logMessage('CommittedFeaturesAdded called', 'AltibasePlugin')

        s_mappedlayer = QgsProject.instance().mapLayer(a_layer)
        s_layerid = s_mappedlayer.id()

        if self.g_layers_error_dic[s_layerid] == 0:
            for s_feature in a_features:
                try:
                    self.g_layers_added_features_dic[s_layerid].append(s_feature.id())
                except Exception as e:
                    iface.messageBar().pushMessage('AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical)
                    self.g_layers_error_dic[s_layerid] = 1

                    mappedlayer.select(s_feature.id())

    def committedAttributeValuesChanges(self, layer, attribute_map):
        QgsMessageLog.logMessage( 'CommittedAttributeValues called', 'AltibasePlugin' )

        query_dic_list = []
        layer_query_dic = {}

        mappedlayer = QgsProject.instance().mapLayer( layer )
        layerid = mappedlayer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        layer_name = layer_info['name'].split('.')
        schema = layer_name[0]
        table = layer_name[1]

        if self.g_layers_error_dic[ layerid ] == 0:
            fields = mappedlayer.fields()
            pk_list_index = fields.names().index( layer_info['pk'] )

            i=0
            for featureid, attributes in attribute_map.items():

                if featureid == self.g_layers_invalid_feature_dic[layerid]:
                    QgsMessageLog.logMessage('Cannot change invalid feature (%s) attribute values.' % str(featureid), 'AltibasePlugin')
                    continue

                query_dic = {}

                try:
                    feature = mappedlayer.getFeature( featureid )

                    ks = []
                    vs = []

                    for k, v in attributes.items():
                        ks.append( '"%s"' % fields.names()[ k ] )
                        if str(v) == "NULL":
                            vs.append( "%s" % v )
                        else:
                            vs.append( "'%s'" % v )

                    # NOTE: 현재의 구현으로는 Primary key column 값을 변경할 수 없다. 이는 변경되기 전 값을 알 수 없기 때문이다.
                    s_query = 'update "%s"."%s" set (%s) = (%s) where "%s" = %s' % ( schema, table,
                                                                        ",".join( ks ),
                                                                        ",".join( vs ),
                                                                        layer_info['pk'],
                                                                        feature[ pk_list_index ] )
                    query_dic['fid'] = featureid
                    query_dic['query'] = s_query
                    query_dic_list.append(query_dic)
                    i = i+1
                except Exception as e:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                    self.g_layers_error_dic[ layerid ] = 1
                    mappedlayer.select( featureid )
                    return

            if i>0:
                dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
                org_query_dic_list = next(dict, False)
                # self.g_layer_querys에 동일 layerid의 querys가 이미 존재하는 경우, 기존꺼에 신규 querys를 extend한다.
                if org_query_dic_list:
                    self.g_layer_querys[self.g_layer_querys.index(org_query_dic_list)]['querys'].extend(query_dic_list)
                else:
                    layer_query_dic['layerId'] = layerid
                    layer_query_dic['querys'] = query_dic_list
                    self.g_layer_querys.append(layer_query_dic)

    def committedGeometriesChanges(self, layer, geometry_map):
        QgsMessageLog.logMessage( 'CommittedGeometriesChanges called', 'AltibasePlugin' )

        query_dic_list = []
        layer_query_dic = {}

        mappedlayer = QgsProject.instance().mapLayer( layer )
        layerid = mappedlayer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        layer_name = layer_info['name'].split('.')
        schema = layer_name[0]
        table = layer_name[1]

        if self.g_layers_error_dic[ layerid ] == 0:
            fields = mappedlayer.fields()
            pk_list_index = fields.names().index( layer_info['pk'] )

            i=0
            for featureid, geometry in geometry_map.items():
                if featureid == self.g_layers_invalid_feature_dic[layerid]:
                    QgsMessageLog.logMessage('Cannot change invalid feature (%s) geometry.' % str(featureid), 'AltibasePlugin')
                    continue

                query_dic = {}

                try:
                    feature = mappedlayer.getFeature( featureid )
                    geom_hex = binascii.b2a_hex( geometry.asWkb() ).decode()

                    s_query = 'update "%s"."%s" set "%s" = st_setsrid(geomfromwkb(BINARY\'%s\'), %s) where "%s" = %s' % ( schema, table,
                                                                                                             layer_info['geom'],
                                                                                                             geom_hex,
                                                                                                             layer_info['srid'],
                                                                                                             layer_info['pk'],
                                                                                                             feature[ pk_list_index ] )
                    query_dic['fid'] = featureid
                    query_dic['query'] = s_query
                    query_dic_list.append(query_dic)
                    i = i+1
                except Exception as e:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                    self.g_layers_error_dic[ layerid ] = 1
                    mappedlayer.select( featureid )
                    return

            if i>0:
                dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
                org_query_dic_list = next(dict, False)
                # self.g_layer_querys에 동일 layerid의 querys가 이미 존재하는 경우, 기존꺼에 신규 querys를 extend한다.
                if org_query_dic_list:
                    self.g_layer_querys[self.g_layer_querys.index(org_query_dic_list)]['querys'].extend(query_dic_list)
                else:
                    layer_query_dic['layerId'] = layerid
                    layer_query_dic['querys'] = query_dic_list
                    self.g_layer_querys.append(layer_query_dic)

    def featureDeleted(self, layer, featureid):
        QgsMessageLog.logMessage( 'FeaturesDeleted called', 'AltibasePlugin' )

        layerid = layer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        if self.g_layers_error_dic[ layerid ] == 0:
            try:
                fields = layer.fields()
                pk_list_index = fields.names().index( layer_info['pk'] )
                features = layer.dataProvider().getFeatures( QgsFeatureRequest().setFilterFid( featureid ) )

                for feature in features:
                    self.g_layers_removed_features_pk_dic[ "%s_%s" % ( layerid, featureid ) ] = feature[ pk_list_index ]

                    try:
                        self.g_layers_added_features_dic[ layerid ].remove( featureid )
                    except:
                        pass

            except Exception as e:
                iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                self.g_layers_error_dic[ layerid ] = 1

                layer.select( featureid )

    def committedFeaturesRemoved(self, layer, featureids):
        QgsMessageLog.logMessage( 'CommittedFeaturesRemoved called', 'AltibasePlugin' )

        mappedlayer = QgsProject.instance().mapLayer( layer )
        layerid = mappedlayer.id()

        if self.g_layers_error_dic[ layerid ] == 0:
            for featureid in featureids:
                try:
                    s_invalid_feature_is_removed = False

                    if featureid == self.g_layers_invalid_feature_dic[layerid]:
                        try:
                            dict = (item['querys'] for item in self.g_layer_querys if item['layerId'] == layerid)
                            query_dic_list = next(dict, False)
                            QgsMessageLog.logMessage( 'before (%s)' % str(query_dic_list) , 'AltibasePlugin' )
                            if query_dic_list:
                                for query_dic in query_dic_list:
                                    if query_dic['fid'] == featureid:
                                        query_dic_list.remove(query_dic)
                                        s_invalid_feature_is_removed = True

                            QgsMessageLog.logMessage( 'after (%s)' % str(query_dic_list) , 'AltibasePlugin' )
                        except Exception as e2:
                            QgsMessageLog.logMessage('Error : {0}'.format(e2), 'AltibasePlugin' )
                            pass

                    if s_invalid_feature_is_removed == False:
                        self.g_layers_removed_features_dic[ layerid ].append( featureid )

                except Exception as e:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                    self.g_layers_error_dic[ layerid ] = 1

                    mappedlayer.select( featureid )

    def editingStarted(self, layer):
        QgsMessageLog.logMessage( 'EditingStarted called... %s[%s]' % (layer.id(), layer.name()), 'AltibasePlugin' )

        self.g_layers_error_dic[ layer.id() ] = 0

    def editingStopped(self, layer):
        QgsMessageLog.logMessage( 'EditingStopped called', 'AltibasePlugin' )

        self.deleteFeaturesFromDb( layer )
        self.insertFeaturesToDb( layer )

        if self.g_layers_error_dic[ layer.id() ] != 0:
            QgsMessageLog.logMessage('[%s] An error was found during the Editing and could not be saved' % layer.id(), 'AltibasePlugin')
            return

        layerid = layer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
        query_dic_list = next(dict, False)
        QgsMessageLog.logMessage('(%s)' % str(query_dic_list), 'AltibasePlugin')

        # layer마다 커넥션 정보가 다를 수 있으므로 매번 connect 수행
        if query_dic_list:
            alti_conn = AltiConn()
            res = alti_conn.connectDB(layer_info['conn_name'])
            if res:
                self.msgbar_logging("warning", res)
            else:
                res_fid = alti_conn.execDMLs(query_dic_list['querys'])
                if res_fid == 0:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Saving done!', Qgis.Info )
                    dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
                    self.g_layer_querys.remove(query_dic_list)
                    self.g_layers_invalid_feature_dic[layerid] = -1
                elif res_fid > 0:
                    layer.select( res_fid )
                    self.g_layers_invalid_feature_dic[layerid] = res_fid
                alti_conn.disconnectDB()

    def deleteFeaturesFromDb(self, layer):
        QgsMessageLog.logMessage( 'deleteFeaturesFromDb called', 'AltibasePlugin' )

        query_dic_list = []
        layer_query_dic = {}

        layerid = layer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        #QgsMessageLog.logMessage('layer_info = %s' % layer_info, 'AltibasePlugin')
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        layer_name = layer_info['name'].split('.')
        schema = layer_name[0]
        table = layer_name[1]

        if self.g_layers_error_dic[ layerid ] == 0:
            i=0
            for featureid in self.g_layers_removed_features_dic[ layerid ]:
                query_dic = {}

                try:
                    s_query = 'delete from "%s"."%s" where "%s" = %s' % ( schema, table,
                                                                 layer_info['pk'],
                                                                 self.g_layers_removed_features_pk_dic[ "%s_%s" % ( layerid, featureid ) ] )
                    query_dic['fid'] = featureid
                    query_dic['query'] = s_query
                    query_dic_list.append(query_dic)
                    i = i+1
                except Exception as e:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                    self.g_layers_error_dic[ layerid ] = 1
                    layer.select( featureid )
                    return

            if i>0:    
                dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
                org_query_dic_list = next(dict, False)
                # self.g_layer_querys에 동일 layerid의 querys가 이미 존재하는 경우, 기존꺼에 신규 querys를 extend한다.
                if org_query_dic_list:
                    self.g_layer_querys[self.g_layer_querys.index(org_query_dic_list)]['querys'].extend(query_dic_list)
                else:
                    layer_query_dic['layerId'] = layerid
                    layer_query_dic['querys'] = query_dic_list
                    self.g_layer_querys.append(layer_query_dic)

            self.g_layers_removed_features_dic[ layerid ].clear()

    def insertFeaturesToDb(self, layer):
        QgsMessageLog.logMessage( 'insertFeaturesToDb called', 'AltibasePlugin' )

        query_dic_list = []
        layer_query_dic = {}

        layerid = layer.id()

        dict = (item for item in self.g_layers_info if item['id'] == layerid)
        layer_info = next(dict, False)
        if not layer_info:
            QgsMessageLog.logMessage('Fail to get layer_info with layer_id(%s)' % layerid, 'AltibasePlugin')
            return

        layer_name = layer_info['name'].split('.')
        schema = layer_name[0]
        table = layer_name[1]

        if self.g_layers_error_dic[ layerid ] == 0:
            fields = layer.fields()

            i=0
            for featureid in self.g_layers_added_features_dic[ layerid ]:
                query_dic = {}

                try:
                    feature = layer.getFeature( featureid )
                    geom_hex = binascii.b2a_hex( feature.geometry().asWkb() ).decode()

                    ks = []
                    ki = 0
                    vs = []

                    for v in feature.attributes():
                        ks.append( '"%s"' % fields.names()[ ki ] )
                        ki += 1
                        if str(v) == "NULL":
                            vs.append( "%s" % v )
                        else:
                            vs.append( "'%s'" % v )

                    ks.append( '"%s"' % layer_info['geom'] )
                    vs.append( "st_setsrid(geomfromwkb(BINARY'%s'), %s)" % ( geom_hex, layer_info['srid'] ) )

                    s_query = 'insert into "%s"."%s" (%s) values (%s)' % ( schema, table,
                                                                    ",".join( ks ),
                                                                    ",".join( vs ) )
                    query_dic['fid'] = featureid
                    query_dic['query'] = s_query
                    query_dic_list.append(query_dic)
                    i = i+1
                    #QgsMessageLog.logMessage('[insertFeaturesToDb] %s' % layerid, 'AltibasePlugin')
                except Exception as e:
                    iface.messageBar().pushMessage( 'AltibasePlugin', 'Error : {0}'.format( e ), Qgis.Critical )
                    self.g_layers_error_dic[ layerid ] = 1
                    layer.select( featureid )
                    return

            if i>0:
                dict = (item for item in self.g_layer_querys if item['layerId'] == layerid)
                org_query_dic_list = next(dict, False)
                # self.g_layer_querys에 동일 layerid의 querys가 이미 존재하는 경우, 기존꺼에 신규 querys를 extend한다.
                if org_query_dic_list:
                    self.g_layer_querys[self.g_layer_querys.index(org_query_dic_list)]['querys'].extend(query_dic_list)
                else:
                    layer_query_dic['layerId'] = layerid
                    layer_query_dic['querys'] = query_dic_list
                    self.g_layer_querys.append(layer_query_dic)
                
            self.g_layers_added_features_dic[ layerid ].clear()
            #QgsMessageLog.logMessage('[insertFeaturesToDb] %s' % str(self.g_layer_querys), 'AltibasePlugin')
