#***************************************************************************
#*                                                                         *
#*   Copyright (c) 2011                                                    *
#*   Yorik van Havre <yorik@uncreated.net>                                 *
#*                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   This program is distributed in the hope that it will be useful,       *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with this program; if not, write to the Free Software   *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#***************************************************************************

import FreeCAD,Draft,math,DraftVecUtils,ArchCommands
from FreeCAD import Vector
if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore, QtGui
    from DraftTools import translate
    from pivy import coin
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt,txt):
        return txt
    def QT_TRANSLATE_NOOP(ctxt,txt):
        return txt
    # \endcond

__title__="FreeCAD Axis System"
__author__ = "Yorik van Havre"
__url__ = "http://www.freecadweb.org"

## @package ArchAxis
#  \ingroup ARCH
#  \brief Axis system for the Arch workbench
#
#  This module provides tools to build axis systems
#  An axis system is a collection of planar axes with a number/tag


def makeAxis(num=5,size=1000,name="Axes"):
    '''makeAxis(num,size): makes an Axis set
    based on the given number of axes and interval distances'''
    obj = FreeCAD.ActiveDocument.addObject("App::FeaturePython",name)
    obj.Label = translate("Arch",name)
    _Axis(obj)
    if FreeCAD.GuiUp:
        _ViewProviderAxis(obj.ViewObject)
    if num:
        dist = []
        angles = []
        for i in range(num):
            dist.append(float(size))
            angles.append(float(0))
        obj.Distances = dist
        obj.Angles = angles
    FreeCAD.ActiveDocument.recompute()
    return obj


def makeAxisSystem(axes,name="Axis System"):
    '''makeAxisSystem(axes): makes a system from the given list of axes'''
    if not isinstance(axes,list):
        axes = [axes]
    obj = FreeCAD.ActiveDocument.addObject("App::FeaturePython",name)
    obj.Label = translate("Arch",name)
    _AxisSystem(obj)
    obj.Axes = axes
    if FreeCAD.GuiUp:
        _ViewProviderAxisSystem(obj.ViewObject)


class _CommandAxis:
    "the Arch Axis command definition"
    def GetResources(self):
        return {'Pixmap'  : 'Arch_Axis',
                'MenuText': QT_TRANSLATE_NOOP("Arch_Axis","Axis"),
                'Accel': "A, X",
                'ToolTip': QT_TRANSLATE_NOOP("Arch_Axis","Creates a set of axes.")}

    def Activated(self):
        FreeCAD.ActiveDocument.openTransaction(translate("Arch","Create Axis"))
        FreeCADGui.addModule("Arch")

        FreeCADGui.doCommand("Arch.makeAxis()")
        FreeCAD.ActiveDocument.commitTransaction()

    def IsActive(self):
        return not FreeCAD.ActiveDocument is None


class _CommandAxisSystem:
    "the Arch Axis System command definition"
    def GetResources(self):
        return {'Pixmap'  : 'Arch_Axis_System',
                'MenuText': QT_TRANSLATE_NOOP("Arch_AxisSystem","Axis System"),
                'Accel': "X, S",
                'ToolTip': QT_TRANSLATE_NOOP("Arch_AxisSystem","Creates an axis system from a set of axes.")}

    def Activated(self):
        if FreeCADGui.Selection.getSelection():
            import Draft
            s = "["
            for o in FreeCADGui.Selection.getSelection():
                if Draft.getType(o) != "Axis":
                    FreeCAD.Console.PrintError(translate("Arch","Only axes must be selected\n"))
                    return
                s += "FreeCAD.ActiveDocument."+o.Name+","
            s += "]"
            FreeCAD.ActiveDocument.openTransaction(translate("Arch","Create Axis System"))
            FreeCADGui.addModule("Arch")
            FreeCADGui.doCommand("Arch.makeAxisSystem("+s+")")
            FreeCAD.ActiveDocument.commitTransaction()
        else:
            FreeCAD.Console.PrintError(translate("Arch","Please select at least one axis\n"))

    def IsActive(self):
        return not FreeCAD.ActiveDocument is None


class _Axis:
    "The Axis object"
    def __init__(self,obj):
        obj.addProperty("App::PropertyFloatList","Distances","Arch", QT_TRANSLATE_NOOP("App::Property","The intervals between axes"))
        obj.addProperty("App::PropertyFloatList","Angles","Arch", QT_TRANSLATE_NOOP("App::Property","The angles of each axis"))
        obj.addProperty("App::PropertyStringList","Labels","Arch", QT_TRANSLATE_NOOP("App::Property","The label of each axis"))
        obj.addProperty("App::PropertyLength","Length","Arch", QT_TRANSLATE_NOOP("App::Property","The length of the axes"))
        obj.addProperty("App::PropertyPlacement","Placement","Base","")
        obj.addProperty("Part::PropertyPartShape","Shape","Base","")
        self.Type = "Axis"
        obj.Length=3000
        obj.Proxy = self

    def execute(self,obj):
        import Part
        geoms = []
        dist = 0
        if obj.Distances:
            if len(obj.Distances) == len(obj.Angles):
                for i in range(len(obj.Distances)):
                    if hasattr(obj.Length,"Value"):
                        l = obj.Length.Value
                    else:
                        l = obj.Length
                    dist += obj.Distances[i]
                    ang = math.radians(obj.Angles[i])
                    p1 = Vector(dist,0,0)
                    p2 = Vector(dist+(l/math.cos(ang))*math.sin(ang),l,0)
                    geoms.append(Part.LineSegment(p1,p2).toShape())
        if geoms:
            sh = Part.Compound(geoms)
            sh.Placement = obj.Placement
            obj.Shape = sh

    def onChanged(self,obj,prop):
        if prop in ["Angles","Distances","Placement"]:
            self.execute(obj)

    def __getstate__(self):
        return self.Type

    def __setstate__(self,state):
        if state:
            self.Type = state

    def getPoints(self,obj):
        "returns the gridpoints of linked axes"
        pts = []
        for e in obj.Shape.Edges:
            pts.append(e.Vertexes[0].Point)
        return pts


class _ViewProviderAxis:
    "A View Provider for the Axis object"

    def __init__(self,vobj):
        vobj.addProperty("App::PropertyLength","BubbleSize","Arch", QT_TRANSLATE_NOOP("App::Property","The size of the axis bubbles"))
        vobj.addProperty("App::PropertyEnumeration","NumberingStyle","Arch", QT_TRANSLATE_NOOP("App::Property","The numbering style"))
        vobj.addProperty("App::PropertyEnumeration","DrawStyle","Base","")
        vobj.addProperty("App::PropertyEnumeration","BubblePosition","Base","")
        vobj.addProperty("App::PropertyFloat","LineWidth","Base","")
        vobj.addProperty("App::PropertyColor","LineColor","Base","")
        vobj.addProperty("App::PropertyInteger","StartNumber","Base","")
        vobj.addProperty("App::PropertyFont","FontName","Base","")
        vobj.addProperty("App::PropertyLength","FontSize","Base","")
        vobj.addProperty("App::PropertyBool","ShowLabel","Base",QT_TRANSLATE_NOOP("App::Property","If true, show the labels"))
        vobj.addProperty("App::PropertyPlacement","LabelOffset","Base",QT_TRANSLATE_NOOP("App::Property","A transformation to apply to each label"))
        vobj.NumberingStyle = ["1,2,3","01,02,03","001,002,003","A,B,C","a,b,c","I,II,III","L0,L1,L2"]
        vobj.DrawStyle = ["Solid","Dashed","Dotted","Dashdot"]
        vobj.BubblePosition = ["Start","End","Both","None"]
        vobj.Proxy = self
        vobj.BubbleSize = 500
        vobj.LineWidth = 1
        vobj.LineColor = (0.13,0.15,0.37)
        vobj.DrawStyle = "Dashdot"
        vobj.NumberingStyle = "1,2,3"
        vobj.StartNumber = 1
        vobj.FontName = Draft.getParam("textfont","Arial,Sans")
        vobj.FontSize = 350
        vobj.ShowLabel = False

    def getIcon(self):
        import Arch_rc
        return ":/icons/Arch_Axis_Tree.svg"

    def claimChildren(self):
        return []

    def attach(self, vobj):
        self.bubbles = None
        self.bubbletexts = []
        sep = coin.SoSeparator()
        self.mat = coin.SoMaterial()
        self.linestyle = coin.SoDrawStyle()
        self.linecoords = coin.SoCoordinate3()
        self.lineset = coin.SoType.fromName("SoBrepEdgeSet").createInstance()
        self.bubbleset = coin.SoSeparator()
        self.labelset = coin.SoSeparator()
        sep.addChild(self.mat)
        sep.addChild(self.linestyle)
        sep.addChild(self.linecoords)
        sep.addChild(self.lineset)
        sep.addChild(self.bubbleset)
        sep.addChild(self.labelset)
        vobj.addDisplayMode(sep,"Default")
        self.onChanged(vobj,"BubbleSize")
        self.onChanged(vobj,"ShowLabel")

    def getDisplayModes(self,vobj):
        return ["Default"]

    def getDefaultDisplayMode(self):
        return "Default"

    def setDisplayMode(self,mode):
        return mode

    def updateData(self,obj,prop):
        if prop == "Shape":
            if obj.Shape:
                if obj.Shape.Edges:
                    verts = []
                    vset = []
                    i = 0
                    for e in obj.Shape.Edges:
                        for v in e.Vertexes:
                            verts.append([v.X,v.Y,v.Z])
                            vset.append(i)
                            i += 1
                        vset.append(-1)
                    self.linecoords.point.setValues(verts)
                    self.lineset.coordIndex.setValues(0,len(vset),vset)
                    self.lineset.coordIndex.setNum(len(vset))
            self.onChanged(obj.ViewObject,"BubbleSize")
            self.onChanged(obj.ViewObject,"ShowLabel")

    def onChanged(self, vobj, prop):
        if prop == "LineColor":
            l = vobj.LineColor
            self.mat.diffuseColor.setValue([l[0],l[1],l[2]])
        elif prop == "DrawStyle":
            if vobj.DrawStyle == "Solid":
                self.linestyle.linePattern = 0xffff
            elif vobj.DrawStyle == "Dashed":
                self.linestyle.linePattern = 0xf00f
            elif vobj.DrawStyle == "Dotted":
                self.linestyle.linePattern = 0x0f0f
            else:
                self.linestyle.linePattern = 0xff88
        elif prop == "LineWidth":
                self.linestyle.lineWidth = vobj.LineWidth
        elif prop in ["BubbleSize","BubblePosition","FontName","FontSize"]:
            if hasattr(self,"bubbleset"):
                if self.bubbles:
                    self.bubbleset.removeChild(self.bubbles)
                    self.bubbles = None
                if vobj.Object.Shape:
                    if vobj.Object.Shape.Edges:
                        self.bubbles = coin.SoSeparator()
                        self.bubblestyle = coin.SoDrawStyle()
                        self.bubblestyle.linePattern = 0xffff
                        self.bubbles.addChild(self.bubblestyle)
                        import Part,Draft
                        self.bubbletexts = []
                        pos = ["Start"]
                        if hasattr(vobj,"BubblePosition"):
                            if vobj.BubblePosition == "Both":
                                pos = ["Start","End"]
                            elif vobj.BubblePosition == "None":
                                pos = []
                            else:
                                pos = [vobj.BubblePosition]
                        for i in range(len(vobj.Object.Shape.Edges)):
                            for p in pos:
                                verts = vobj.Object.Shape.Edges[i].Vertexes
                                if p == "Start":
                                    p1 = verts[0].Point
                                    p2 = verts[1].Point
                                else:
                                    p1 = verts[1].Point
                                    p2 = verts[0].Point
                                dv = p2.sub(p1)
                                dv.normalize()
                                if hasattr(vobj.BubbleSize,"Value"):
                                    rad = vobj.BubbleSize.Value/2
                                else:
                                    rad = vobj.BubbleSize/2
                                center = p2.add(dv.scale(rad,rad,rad))
                                buf = Part.makeCircle(rad,center).writeInventor()
                                try:
                                    cin = coin.SoInput()
                                    cin.setBuffer(buf)
                                    cob = coin.SoDB.readAll(cin)
                                except:
                                    import re
                                    # workaround for pivy SoInput.setBuffer() bug
                                    buf = buf.replace("\n","")
                                    pts = re.findall("point \[(.*?)\]",buf)[0]
                                    pts = pts.split(",")
                                    pc = []
                                    for p in pts:
                                        v = p.strip().split()
                                        pc.append([float(v[0]),float(v[1]),float(v[2])])
                                    coords = coin.SoCoordinate3()
                                    coords.point.setValues(0,len(pc),pc)
                                    line = coin.SoLineSet()
                                    line.numVertices.setValue(-1)
                                else:
                                    coords = cob.getChild(1).getChild(0).getChild(2)
                                    line = cob.getChild(1).getChild(0).getChild(3)
                                self.bubbles.addChild(coords)
                                self.bubbles.addChild(line)
                                st = coin.SoSeparator()
                                tr = coin.SoTransform()
                                fs = rad*1.5
                                if hasattr(vobj,"FontSize"):
                                    fs = vobj.FontSize.Value
                                tr.translation.setValue((center.x,center.y-fs/2.5,center.z))
                                fo = coin.SoFont()
                                fn = Draft.getParam("textfont","Arial,Sans")
                                if hasattr(vobj,"FontName"):
                                    if vobj.FontName:
                                        try:
                                            fn = str(vobj.FontName)
                                        except:
                                            pass
                                fo.name = fn
                                fo.size = fs
                                tx = coin.SoAsciiText()
                                tx.justification = coin.SoText2.CENTER
                                self.bubbletexts.append(tx)
                                st.addChild(tr)
                                st.addChild(fo)
                                st.addChild(tx)
                                self.bubbles.addChild(st)
                        self.bubbleset.addChild(self.bubbles)
                        self.onChanged(vobj,"NumberingStyle")
            if prop in ["FontName","FontSize"]:
                self.onChanged(vobj,"ShowLabel")
        elif prop in ["NumberingStyle","StartNumber"]:
            if hasattr(self,"bubbletexts"):
                chars = "abcdefghijklmnopqrstuvwxyz"
                roman=(('M',1000),('CM',900),('D',500),('CD',400),
                       ('C',100),('XC',90),('L',50),('XL',40),
                       ('X',10),('IX',9),('V',5),('IV',4),('I',1))
                num = 0
                if hasattr(vobj,"StartNumber"):
                    if vobj.StartNumber > 1:
                        num = vobj.StartNumber-1
                alt = False
                for t in self.bubbletexts:
                    if hasattr(vobj,"NumberingStyle"):
                        if vobj.NumberingStyle == "1,2,3":
                            t.string = str(num+1)
                        elif vobj.NumberingStyle == "01,02,03":
                            t.string = str(num+1).zfill(2)
                        elif vobj.NumberingStyle == "001,002,003":
                            t.string = str(num+1).zfill(3)
                        elif vobj.NumberingStyle == "A,B,C":
                            result = ""
                            base = num/26
                            if base:
                                result += chars[base].upper()
                            remainder = num % 26
                            result += chars[remainder].upper()
                            t.string = result
                        elif vobj.NumberingStyle == "a,b,c":
                            result = ""
                            base = num/26
                            if base:
                                result += chars[base]
                            remainder = num % 26
                            result += chars[remainder]
                            t.string = result
                        elif vobj.NumberingStyle == "I,II,III":
                            result = ""
                            n = num
                            n += 1
                            for numeral, integer in roman:
                                while n >= integer:
                                    result += numeral
                                    n -= integer
                            t.string = result
                        elif vobj.NumberingStyle == "L0,L1,L2":
                            t.string = "L"+str(num)
                    else:
                        t.string = str(num+1)
                    num += 1
                    if hasattr(vobj,"BubblePosition"):
                        if vobj.BubblePosition == "Both":
                            if not alt:
                                num -= 1
                    alt = not alt
        elif prop in ["ShowLabel", "LabelOffset"]:
            if hasattr(self,"labels"):
                if self.labels:
                    self.labelset.removeChild(self.labels)
            self.labels = None
            if hasattr(vobj,"ShowLabel") and hasattr(vobj.Object,"Labels"):
                if vobj.ShowLabel:
                    self.labels = coin.SoSeparator()
                    for i in range(len(vobj.Object.Shape.Edges)):
                        if len(vobj.Object.Labels) > i:
                            if vobj.Object.Labels[i]:
                                import Draft
                                vert = vobj.Object.Shape.Edges[i].Vertexes[0].Point
                                if hasattr(vobj,"LabelOffset"):
                                    pl = FreeCAD.Placement(vobj.LabelOffset)
                                    pl.Base = vert.add(pl.Base)
                                st = coin.SoSeparator()
                                tr = coin.SoTransform()
                                fo = coin.SoFont()
                                tx = coin.SoAsciiText()
                                tx.justification = coin.SoText2.LEFT
                                t = vobj.Object.Labels[i]
                                if isinstance(t,unicode):
                                    t = t.encode("utf8")
                                tx.string.setValue(t)
                                if hasattr(vobj,"FontSize"):
                                    fs = vobj.FontSize.Value
                                elif hasattr(vobj.BubbleSize,"Value"):
                                    fs = vobj.BubbleSize.Value*0.75
                                else:
                                    fs = vobj.BubbleSize*0.75
                                tr.translation.setValue(tuple(pl.Base))
                                tr.rotation.setValue(pl.Rotation.Q)
                                fn = Draft.getParam("textfont","Arial,Sans")
                                if hasattr(vobj,"FontName"):
                                    if vobj.FontName:
                                        try:
                                            fn = str(vobj.FontName)
                                        except:
                                            pass
                                fo.name = fn
                                fo.size = fs
                                st.addChild(tr)
                                st.addChild(fo)
                                st.addChild(tx)
                                self.labels.addChild(st)
                    self.labelset.addChild(self.labels)


    def setEdit(self,vobj,mode=0):
        taskd = _AxisTaskPanel()
        taskd.obj = vobj.Object
        taskd.update()
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self,vobj,mode):
        FreeCADGui.Control.closeDialog()
        return

    def doubleClicked(self,vobj):
        self.setEdit(vobj)

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None


class _AxisTaskPanel:
    '''The editmode TaskPanel for Axis objects'''
    def __init__(self):
        # the panel has a tree widget that contains categories
        # for the subcomponents, such as additions, subtractions.
        # the categories are shown only if they are not empty.

        self.updating = False

        self.obj = None
        self.form = QtGui.QWidget()
        self.form.setObjectName("TaskPanel")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.title = QtGui.QLabel(self.form)
        self.grid.addWidget(self.title, 0, 0, 1, 2)

        # tree
        self.tree = QtGui.QTreeWidget(self.form)
        self.grid.addWidget(self.tree, 1, 0, 1, 2)
        self.tree.setColumnCount(4)
        self.tree.header().resizeSection(0,50)
        self.tree.header().resizeSection(1,80)
        self.tree.header().resizeSection(2,60)

        # buttons
        self.addButton = QtGui.QPushButton(self.form)
        self.addButton.setObjectName("addButton")
        self.addButton.setIcon(QtGui.QIcon(":/icons/Arch_Add.svg"))
        self.grid.addWidget(self.addButton, 3, 0, 1, 1)
        self.addButton.setEnabled(True)

        self.delButton = QtGui.QPushButton(self.form)
        self.delButton.setObjectName("delButton")
        self.delButton.setIcon(QtGui.QIcon(":/icons/Arch_Remove.svg"))
        self.grid.addWidget(self.delButton, 3, 1, 1, 1)
        self.delButton.setEnabled(True)

        QtCore.QObject.connect(self.addButton, QtCore.SIGNAL("clicked()"), self.addElement)
        QtCore.QObject.connect(self.delButton, QtCore.SIGNAL("clicked()"), self.removeElement)
        QtCore.QObject.connect(self.tree, QtCore.SIGNAL("itemChanged(QTreeWidgetItem *, int)"), self.edit)
        self.update()

    def isAllowedAlterSelection(self):
        return False

    def isAllowedAlterView(self):
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Close)

    def update(self):
        'fills the treewidget'
        self.updating = True
        self.tree.clear()
        if self.obj:
            for i in range(len(self.obj.Distances)):
                item = QtGui.QTreeWidgetItem(self.tree)
                item.setText(0,str(i+1))
                if len(self.obj.Distances) > i:
                    item.setText(1,str(self.obj.Distances[i]))
                if len(self.obj.Angles) > i:
                    item.setText(2,str(self.obj.Angles[i]))
                if hasattr(self.obj,"Labels"):
                    if len(self.obj.Labels) > i:
                        item.setText(3,str(self.obj.Labels[i]))
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                item.setTextAlignment(0,QtCore.Qt.AlignLeft)
        self.retranslateUi(self.form)
        self.updating = False

    def addElement(self):
        item = QtGui.QTreeWidgetItem(self.tree)
        item.setText(0,str(self.tree.topLevelItemCount()))
        item.setText(1,"1.0")
        item.setText(2,"0.0")
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.resetObject()

    def removeElement(self):
        it = self.tree.currentItem()
        if it:
            nr = int(it.text(0))-1
            self.resetObject(remove=nr)
            self.update()

    def edit(self,item,column):
        if not self.updating:
            self.resetObject()

    def resetObject(self,remove=None):
        "transfers the values from the widget to the object"
        d = []
        a = []
        l = []
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.findItems(str(i+1),QtCore.Qt.MatchExactly,0)[0]
            if (remove == None) or (remove != i):
                if it.text(1):
                    d.append(float(it.text(1)))
                else:
                    d.append(0.0)
                if it.text(2):
                    a.append(float(it.text(2)))
                else:
                    a.append(0.0)
                l.append(it.text(3))
        self.obj.Distances = d
        self.obj.Angles = a
        self.obj.Labels = l
        self.obj.touch()
        FreeCAD.ActiveDocument.recompute()

    def reject(self):
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.ActiveDocument.resetEdit()
        return True

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle(QtGui.QApplication.translate("Arch", "Axes", None))
        self.delButton.setText(QtGui.QApplication.translate("Arch", "Remove", None))
        self.addButton.setText(QtGui.QApplication.translate("Arch", "Add", None))
        self.title.setText(QtGui.QApplication.translate("Arch", "Distances (mm) and angles (deg) between axes", None))
        self.tree.setHeaderLabels([QtGui.QApplication.translate("Arch", "Axis", None),
                                   QtGui.QApplication.translate("Arch", "Distance", None),
                                   QtGui.QApplication.translate("Arch", "Angle", None),
                                   QtGui.QApplication.translate("Arch", "Label", None)])


class _AxisSystem:
    "The Axis System object"
    def __init__(self,obj):
        obj.addProperty("App::PropertyLinkList","Axes","Arch", QT_TRANSLATE_NOOP("App::Property","The axes this system is made of"))
        obj.addProperty("App::PropertyPlacement","Placement","Base","")
        self.Type = "AxisSystem"
        obj.Proxy = self

    def execute(self,obj):
        pass

    def onBeforeChange(self,obj,prop):
        if prop == "Placement":
            self.Placement = obj.Placement

    def onChanged(self,obj,prop):
        if prop == "Placement":
            if hasattr(self,"Placement"):
                delta = obj.Placement.multiply(self.Placement.inverse())
                for o in obj.Axes:
                    o.Placement = delta.multiply(o.Placement)

    def __getstate__(self):
        return self.Type

    def __setstate__(self,state):
        if state:
            self.Type = state

    def getPoints(self,obj):
        "returns the gridpoints of linked axes"
        import DraftGeomUtils
        pts = []
        if len(obj.Axes) == 1:
            for e in obj.Axes[0].Shape.Edges:
                pts.append(e.Vertexes[0].Point)
        elif len(obj.Axes) == 2:
            set1 = obj.Axes[0].Shape.Edges # X
            set2 = obj.Axes[1].Shape.Edges # Y
            for e1 in set1:
                for e2 in set2:
                    pts.extend(DraftGeomUtils.findIntersection(e1,e2))
        elif len(obj.Axes) == 3:
            set1 = obj.Axes[0].Shape.Edges # X
            set2 = obj.Axes[1].Shape.Edges # Y
            set3 = obj.Axes[2].Shape.Edges # Z
            bset = []
            cv = None
            for e1 in set1:
                for e2 in set2:
                    bset.extend(DraftGeomUtils.findIntersection(e1,e2))
            for e3 in set3:
                if not cv:
                    cv = e3.Vertexes[0].Point
                    pts.extend(bset)
                else:
                    cv = e3.Vertexes[0].Point.sub(vc)
                    pts.extend([p.add(cv) for p in bset])
        return pts


class _ViewProviderAxisSystem:
    "A View Provider for the Axis object"

    def __init__(self,vobj):
        vobj.Proxy = self

    def getIcon(self):
        import Arch_rc
        return ":/icons/Arch_Axis_System_Tree.svg"

    def claimChildren(self):
        if hasattr(self,"axes"):
            return self.axes
        return []

    def attach(self, vobj):
        self.axes = vobj.Object.Axes

    def getDisplayModes(self,vobj):
        return ["Default"]

    def getDefaultDisplayMode(self):
        return "Default"

    def setDisplayMode(self,mode):
        return mode

    def updateData(self,obj,prop):
        self.axes = obj.Axes

    def onChanged(self, vobj, prop):
        if prop == "Visibility":
            for o in vobj.Object.Axes:
                o.ViewObject.Visibility = vobj.Visibility

    def setEdit(self,vobj,mode=0):
        taskd = AxisSystemTaskPanel(vobj.Object)
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self,vobj,mode):
        FreeCADGui.Control.closeDialog()
        return

    def doubleClicked(self,vobj):
        self.setEdit(vobj)

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None


class AxisSystemTaskPanel:
    '''A TaskPanel for all the section plane object'''
    def __init__(self,obj):

        self.obj = obj
        self.form = QtGui.QWidget()
        self.form.setObjectName("Axis System")
        self.grid = QtGui.QGridLayout(self.form)
        self.grid.setObjectName("grid")
        self.title = QtGui.QLabel(self.form)
        self.grid.addWidget(self.title, 0, 0, 1, 2)

        # tree
        self.tree = QtGui.QTreeWidget(self.form)
        self.grid.addWidget(self.tree, 1, 0, 1, 2)
        self.tree.setColumnCount(1)
        self.tree.header().hide()

        # buttons
        self.addButton = QtGui.QPushButton(self.form)
        self.addButton.setObjectName("addButton")
        self.addButton.setIcon(QtGui.QIcon(":/icons/Arch_Add.svg"))
        self.grid.addWidget(self.addButton, 3, 0, 1, 1)

        self.delButton = QtGui.QPushButton(self.form)
        self.delButton.setObjectName("delButton")
        self.delButton.setIcon(QtGui.QIcon(":/icons/Arch_Remove.svg"))
        self.grid.addWidget(self.delButton, 3, 1, 1, 1)

        QtCore.QObject.connect(self.addButton, QtCore.SIGNAL("clicked()"), self.addElement)
        QtCore.QObject.connect(self.delButton, QtCore.SIGNAL("clicked()"), self.removeElement)
        self.update()

    def isAllowedAlterSelection(self):
        return True

    def isAllowedAlterView(self):
        return True

    def getStandardButtons(self):
        return int(QtGui.QDialogButtonBox.Ok)

    def getIcon(self,obj):
        if hasattr(obj.ViewObject,"Proxy"):
            return QtGui.QIcon(obj.ViewObject.Proxy.getIcon())
        elif obj.isDerivedFrom("Sketcher::SketchObject"):
            return QtGui.QIcon(":/icons/Sketcher_Sketch.svg")
        elif obj.isDerivedFrom("App::DocumentObjectGroup"):
            return QtGui.QApplication.style().standardIcon(QtGui.QStyle.SP_DirIcon)
        else:
            return QtGui.QIcon(":/icons/Tree_Part.svg")

    def update(self):
        self.tree.clear()
        if self.obj:
            for o in self.obj.Axes:
                item = QtGui.QTreeWidgetItem(self.tree)
                item.setText(0,o.Label)
                item.setToolTip(0,o.Name)
                item.setIcon(0,self.getIcon(o))
        self.retranslateUi(self.form)

    def addElement(self):
        if self.obj:
            for o in FreeCADGui.Selection.getSelection():
                if (not(o in self.obj.Axes)) and (o != self.obj):
                    g = self.obj.Axes
                    g.append(o)
                    self.obj.Axes = g
            self.update()

    def removeElement(self):
        if self.obj:
            it = self.tree.currentItem()
            if it:
                o = FreeCAD.ActiveDocument.getObject(str(it.toolTip(0)))
                if o in self.obj.Axes:
                    g = self.obj.Axes
                    g.remove(o)
                    self.obj.Axes = g
            self.update()

    def accept(self):
        FreeCAD.ActiveDocument.recompute()
        FreeCADGui.ActiveDocument.resetEdit()
        return True

    def retranslateUi(self, TaskPanel):
        TaskPanel.setWindowTitle(QtGui.QApplication.translate("Arch", "Axes", None))
        self.delButton.setText(QtGui.QApplication.translate("Arch", "Remove", None))
        self.addButton.setText(QtGui.QApplication.translate("Arch", "Add", None))
        self.title.setText(QtGui.QApplication.translate("Arch", "Axis system components", None))


if FreeCAD.GuiUp:
    FreeCADGui.addCommand('Arch_Axis',_CommandAxis())
    FreeCADGui.addCommand('Arch_AxisSystem',_CommandAxisSystem())

    class _ArchAxisGroupCommand:

        def GetCommands(self):
            return tuple(['Arch_Axis','Arch_AxisSystem'])
        def GetResources(self):
            return { 'MenuText': QT_TRANSLATE_NOOP("Arch_AxisTools",'Axis tools'),
                     'ToolTip': QT_TRANSLATE_NOOP("Arch_AxisTools",'Axis tools')
                   }
        def IsActive(self):
            return not FreeCAD.ActiveDocument is None

    FreeCADGui.addCommand('Arch_AxisTools', _ArchAxisGroupCommand())
