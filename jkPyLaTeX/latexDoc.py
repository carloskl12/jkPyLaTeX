import os
import subprocess
import re
from shutil import copyfile,copy

# recursos propios
from jkPyLaTeX import LatexCommand , LatexPackage , PACKAGES
from jkPyLaTeX import CMD_LATEX
'''
El modo de uso consiste en declarar los comandos a usar y la 
clase se encargaría de administrar los paquetes
'''

class LatexDoc(object):
  '''
  Encapsula un fichero latex
  '''
  __version='0.1'
  def __init__(self,name,**kwargs):
    self._name=name
    self._fname=None #Nombre del archivo tex de salida
    self._dirOut='' #Directorio de salida
    #Indica si se utiliza un template externo para el preámbulo
    self._externalPreamble=False 
    #Guarda los diferentes contenidos para el preámbulo
    #Con un respectivo orden respecto a la declaración de paquetes
    self._preamble=[]
    #String al final del preambulo
    self._sEndPreamble=''
    #Guarda los paquetes necesarios
    self._packs={}
    #dic de comandos utilizados
    self._cmd=PACKAGES['global'].copy()
    #lista de redefiniciones
    self._renewcmd=[]
    #lista de nuevos comandos
    self._newcmd=[]
    #Contenido del texto
    self._s='%% contenido\n'
    self.__docIni = None #Inicio del documento para make title, etc.
    #Diccionario con fragmentos de codigo latex que se pueden 
    #llamar desde el documento principal pytex
    self._slice={}
    self._mainSlice=None #Documento principal
    #Parámetros de configuración
    self._cfg_tree=None #Arbol de organización de archivos 
    self._cfg_docclass='article'
    self._cfg_paper=None
    self._cfg_fontsize=None
    self._cfg_language=None
    #Configuración de páginas
    #Las unidades pueden ser cm, in (pulgadas), pt (1cm = 28.5 pt)
    #Los valores tambien pueden ser negativos
    self._cfg_parskip=None # espacio entre parrafos
    #Espacio para encuadernación que afecta la numeración impar si es de
    #impresion a doble cara, de lo contrario afecta a todas las páginas.
    self._cfg_oddsidemargin=None
    self._cfg_headheight=None #Altura del encabezado
    self._cfg_headsep=None  #Espacio entre la base del encabezado y el tope del cuerpo del documento
    self._cfg_marginparsep=None #Distancia que separa las notas marginales del texto principal
    self._cfg_marginparwidth=None# Ancho de las notas marginales (A la derecha)
    self._cfg_footskip=None# Distancia entre el texto y el pie de página.
    #Márgenes de pagina
    self._cfg_top=None
    self._cfg_bottom=None
    self._cfg_left=None
    self._cfg_right=None
    
    self._cfg_lhead=None
    self._cfg_chead=None
    self._cfg_rhead=None
    self._cfg_lfoot=None
    self._cfg_cfoot=None
    self._cfg_rfoot=None
    
    self._cfg_headrulewidth=None
    self._cfg_footrulewidth=None
    
    self._cfg_debug= False
    #\usepackage[top=30mm, bottom=25mm, left=20mm, right=20mm]{geometry}
    
    for k, v in kwargs.items():
      nameParam='_cfg_'+k
      if hasattr(self,nameParam):
        setattr(self,nameParam,v)
      else:
        raise Exception("Error: LatexDoc don't have the param '%s'."%k)
  
   
  @property
  def name(self):
    return self._name
  @property
  def content(self):
    return self._s
    
  @property
  def dirOut(self):
    return self._dirOut
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def __call__(self,*args):
    '''
    Agrega la cadena s generada 
    por el comando cmd
    '''
    for s in args:
      self._s+=s

  def Clear(self):
    '''
    Borra todo el contenido
    '''
    self._s=''
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def _makefile(self, target='*.tex',clean=True):
    '''
    Crea un makefile para compilar el documento latex 
    dado por target
    '''
    s='# makefile creado por jkPyLaTeX\n'
    s3=''
    if target =='*.tex':
      #Compila todo archivo .tex existente
      s+='ARCHIVOS_TEX:= $(wildcard *.tex)\n\n'
      s+='COMPILA:= $(patsubst %.tex, pdflatex -shell-escape '
      s+='-interaction=nonstopmode -halt-on-error %.tex; ,$(ARCHIVOS_TEX))\n\n'
      s1='compilayborra: $(ARCHIVOS_TEX)\n'
      s1+='\t$(COMPILA)\n'
      s1+='\t@make clean\n\n'
      s2='compila: $(ARCHIVOS_TEX)\n'
      s2+='\t$(COMPILA)\n'
    else:
      s+='ARCHIVO_TEX:= %s\n\n'%target
      s1='compilayborra: $(ARCHIVO_TEX)\n'
      s1+='\tpdflatex -shell-escape -interaction=nonstopmode -halt-on-error $(ARCHIVO_TEX)\n'
      s1+='\t@make clean\n\n'
      s2='compila: $(ARCHIVO_TEX)\n'
      s2+='\tpdflatex -shell-escape -interaction=nonstopmode -halt-on-error $(ARCHIVO_TEX)\n'
      
      aux = os.path.splitext(target)[0]+'.aux'
      s3="bib: %s\n"% aux
      s3+="\tbibtex %s\n"%aux
    if clean:
      # Orden de prioridad al llamar make
      # con s1 de primero se indica que se limpia el directorio
      # y s2 es una compilación sin borrar
      s+=s1
      s+=s2
    else:
      s+=s2
      s+=s1
    # agrega el comando para bibtex
    s+= s3
    
    # Declara ficheros ficticios que no se confundan con archivos
    s+='.PHONY: clean\n\n' 
    # Se crea el clean, par alos rm se usa un || para evitar
    # el error cuando no hay archivos que eliminar
    s+='clean:\n'
    s+='\trm *.aux || true\n'
    s+='\trm *.log || true\n'
    s+='\trm *.out || true\n'
    return s
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def getTree(self,dirOut,clean=True):
    '''
    Verifica si existen los respectivos
    directorios con el respectivo makefile.
    En caso contrario los genera
    y retorna las direcciones donde 
    se organizan los archivos fuente,
    figuras y el documento principal
    '''
    #Obtiene el directorio absoluto
    dir_path = os.path.dirname(os.path.realpath(__file__))
    
    if dirOut[-1] !='/':
      dirOut=dirOut+'/'
    srcDir=self._cfg_tree['preamble']
    figsDir=self._cfg_tree['figures']
    srcDir=dirOut+srcDir.replace('./','')
    figsDir=dirOut+figsDir.replace('./','')
    
    if not os.path.isdir(dirOut):
      '''
      Si no existe el directorio crea todos 
      los archivos apartir de texKernel
      '''
      os.makedirs(dirOut)
      os.makedirs(srcDir)
      os.makedirs(figsDir)
      
    else:
      if not os.path.isdir(srcDir):
        os.makedirs(srcDir)
      if not os.path.isdir(figsDir):
        os.makedirs(figsDir)

    
    if not os.path.exists(figsDir+'logo.pdf'):
      if os.path.exists('logo.pdf'):
        copy('logo.pdf',figsDir)
      else:
        logodir= os.path.join(dir_path,'logo.pdf')
        copy(logodir,figsDir)
    if not os.path.exists(figsDir+'logo.png'):
      if os.path.exists('logo.png'):
        copy('logo.png',figsDir)

    return {'dirOut':dirOut ,'src':srcDir,'figs':figsDir}
  
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def addSlice(self, name, content):
    '''
    Agrega un trozo de código al diccionario de trozos
    '''
    if name in self._slice:
      raise Exception('The name "%s" already exists'%name)
    self._slice[name]=content
  
  def setMainSlice(self,fname):
    '''
    Agrega el directorio donde se halla el documento 
    donde se halla el codigo latex y llamadas a los 
    slices dentro de dicho codigo
    '''
    if not os.path.exists(fname):
      raise Exception('The file "%s" does not exist.'%fname)
    self._mainSlice=fname
    
  def jointSlice(self):
    '''
    Procesa el slice principal
    para guardar obtener un
    fragmento tex compilable
    '''
    p = re.compile(r'\\usepytex{([a-zA-Z_]+[0-9a-zA-Z_]*)}')
    pcomment=re.compile(r'^[ ]*[%]')
    mainS='%%%%% main slice \n'
    with open(self._mainSlice,'r') as f:
      for line in  f.readlines():
        newLine=line
        if pcomment.match(line):
          mainS+=newLine
          continue
        for match in p.finditer(line):
          sliceName=match.group(1)
          if not sliceName in self._slice:
            raise Exception("The slice %s don't exist."%sliceName)
          newLine=newLine.replace(match.group(0), self._slice[sliceName])
        mainS+=newLine
    mainS+='\n'
    return mainS
        
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def save(self,fname='./'):
    '''
    Guarda el documento en el directorio
    especificado terminando con /
    '''
    tree=self.getTree(fname)
    fname=tree['dirOut']+self._name
    self._dirOut=tree['dirOut']
    if not ( fname.split(".")[-1]=='tex'):
      fname+=".tex"
    self._fname=fname
    sP=self.preamble()
    dirPreamble=self._cfg_tree['preamble']+'preamble.tex'
    s='%%%%%%%%%%%%%%%%%%%%%\n'
    s+='%%%% LatexDoc v'+self.__version
    s+='\n\\input{%s}'%(dirPreamble)
    if self._externalPreamble:
      # Se utiliza para la redefinición de comandos cuando 
      # se utiliza un preámbulo externo, pues esta parte 
      # no se tendría en cuenta
      sRenewCmd=''
      for rnw in self._renewcmd:
        sRenewCmd+='%s\n'%rnw
      if sRenewCmd != '':
        sMsg='%%%%%%%%%%%% Renombrado de comandos'
        sMsg+='%%%%%%%%%%%%%\n'
        sRenewCmd=sMsg+sRenewCmd
      s+=sRenewCmd
    s+='\n\\begin{document}\n'
    if self._cfg_language != 'english':
      s+='\\selectlanguage{%s}\n'%self._cfg_language
    if self.__docIni != None:
      s+=self.__docIni
    
    if self._mainSlice !=None:
      s+=self.jointSlice()
    s+=self._s+'\n' #Agrega el contenido generado con __call__
    s+='\\end{document}\n'
    with open(fname,'w') as f:
      f.write(s)
    dirPreamble=tree['dirOut']+dirPreamble.replace('./','')
    with open(dirPreamble,'w') as f:
      f.write(sP)
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def pageConfig(self):
    '''
    Configuración de márgenes página
    '''
    #Configuración de páginas
    #Las unidades pueden ser cm, in (pulgadas), pt (1cm = 28.5 pt)
    #Los valores tambien pueden ser negativos
    s=''
    for cfg in ('parskip','oddsidemargin','headheight', 
    'headsep','marginparsep', 'marginparwidth','footskip'):
      cfgN='_cfg_'+cfg
      cfgV=getattr(self,cfgN)
      if cfgV != None:
        s+='\\%s %s\n'%(cfg,cfgV)
    #Opciones para el paquete geometry
    optGeometry=''
    for cfg in ('top','bottom','left','right'):
      cfgN='_cfg_'+cfg
      cfgV=getattr(self,cfgN)
      if cfgV != None:
        if optGeometry !='':
          optGeometry+=', '
        optGeometry+='%s=%s'%(cfg,cfgV)
    if self._cfg_debug:
      print('geometry opt', optGeometry)
    if optGeometry != '':
      if not( 'geometry' in self._packs):
        self._packs['geometry']=PACKAGES['geometry']
      self._packs['geometry'].addOption(optGeometry)
      if self._cfg_debug:
        print('geometry available', 'geometry' in self._packs)
    if s != '':
      s='%%%%%%%%%%%% Configuración de márgenes %%%%%%%%%%%%%%%\n'+s
    
    if self._cfg_debug:
        print(' margenes:', s)
    return s

  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def useCmd(self,cmdName):
    '''
    Declara el uso de un comando para poder registrar que paquetes 
    se requieren declarar
    '''
    if cmdName in self._cmd:
      return self._cmd[cmdName]
    else:
      cmd=None
      for k, pack in self._packs.items():
        if cmdName in pack:
          cmd=pack[cmdName]
          break
      if cmd == None:
        for k, pack in PACKAGES.items():
          if k in self._packs or k == 'global':
            continue
          if cmdName in pack:
            self._packs[k]=pack
            
            cmd=pack[cmdName]
            break
      if cmd == None:
        # Se debe agregar el comando en latexPackages de forma adecuada
        # si se genera este error
        raise Exception("Error: don't exist the command \"%s\""%cmdName)
      self._cmd[cmdName]=cmd
      return cmd
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def renewcommand(self,cmdName,value):
    '''
    Declara la redefinición de comandos
    '''
    s="\\renewcommand{\\%s}{%s}"%(cmdName,value)
    self._renewcmd.append(s)
    if self._externalPreamble:
      return
    if not( cmdName in PACKAGES['global'] or cmdName in self._cmd):
      self.useCmd(cmdName)

  def newcommand(self,cmdName,body,numargs=0,package='default',info=''):
    '''
    Genera un nuevo comando
    '''
    if cmdName in self._cmd:
      print(self._cmd[cmdName])
      raise Exception('Error in newcommand, the command "%s" already exists'%cmdName)
    cmd= LatexCommand(cmdName,body,numargs,package,info)
    self._newcmd.append(cmd)
    self._cmd[cmdName]=cmd
    return cmd
  
  def cmdParser(self,sentence):
    '''
    Analiza una sentencia latex para 
    ver si es posible garantizar 
    que el documento puede usar los 
    comandos garantizando los paquetes
    cargados en el preambulo
    '''
    p = re.compile(r'\\([a-zA-Z]+)')
    commands=[]
    for match in p.finditer(sentence):
      if self._cfg_debug:
        print( 'result:',match.group(1))
      commands.append(match.group(1))
    
    for cmdName in commands:
      if cmdName in CMD_LATEX:
        if not (cmdName in self._cmd):
          cmd=CMD_LATEX[cmdName]
          if not ( cmd.package in self._packs):
            if cmd.package in PACKAGES:
              self._packs[cmd.package]=PACKAGES[cmd.package]
            else:
              raise Exception("Can't find the package "+ cmd.package)
          
          #Verifica el cuerpo del nuevo comando 
          #para definir los comandos 
          #necesarios o cargar paquetes requeridos.
          self.cmdParser(cmd.body)
          self._newcmd.append(cmd)
          self._cmd[cmdName]=cmd
      else:
        self.useCmd(cmdName)
    
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def pageStyle(self):
    '''
    Genera la configuración del estilo de página 
    utilizando fancyhdr
    '''
    
    
    s=''
    if 'geometry' in self._packs:
      s=self._packs['geometry']()
    
    sfancy=''
    for cfg in ('lhead','chead','rhead', 
    'lfoot','cfoot', 'rfoot'):
      cfgN='_cfg_'+cfg
      cfgV=getattr(self,cfgN)
      if cfgV != None:
        sfancy+='\\%s{%s}\n'%(cfg,cfgV)
    
    if sfancy!='':
      #Activa para que los encabezado y pie de páginas
      #sean efectivos
      s+='\\pagestyle{fancy}\n\n'+sfancy
    for cfg in ('headrulewidth','footrulewidth'):
      cfgN='_cfg_'+cfg
      cfgV=getattr(self,cfgN)
      if cfgV != None:
        s+='\\renewcommand{\\%s}{%s}\n'%(cfg,cfgV)
    if sfancy!='' and not( 'fancyhdr' in self._packs) :
        self._packs['fancyhdr']=PACKAGES['fancyhdr']
    if self._cfg_debug:
        print("pagestyle:%%%%%%%%%%%%%%%%%%%\n",s)
    return s

  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def preamble(self,build=False, texTemplate=None,append=''):
    '''
    Crea el preámbulo ajustándose a la configuración
    y los requerimientos del documento, o se toma 
    de una plantilla ya existente que se suministra con 
    texTemplate, 
    * append: es algo que se puede agregar al final del preambulo si hay un
      template, en caso contrario se debe usar appendPreamble
    
    Si ya se ha invocado antes se retorna el 
    valor anterior, en caso de requerir
    una nueva genereación del preámbulo 
    se indica mediante build
    '''
    if texTemplate !=None:
      with open(texTemplate,'r') as f:
        self._spreamble=str(f.read())
      self._sEndPreamble+=append
      self._externalPreamble=True #Indica que se utilizó un template externo
      return self._spreamble
    if hasattr(self,'_spreamble') and not build:
      return self._spreamble
    sRenewCmd=''
    for rnw in self._renewcmd:
      sRenewCmd+='%s\n'%rnw
    if sRenewCmd != '':
      sMsg='%%%%%%%%%%%% Renombrado de comandos'
      sMsg+='%%%%%%%%%%%%%\n'
      sRenewCmd=sMsg+sRenewCmd
    
    sNewCmd=''
    for nw in self._newcmd:
      sNewCmd+='%s\n'%nw.declara()
    if sNewCmd != '':
      sMsg='%%%%%%%%%%%% Declaración de nuevos comandos'
      sMsg+='%%%%%%%%%%%%%\n'
      sNewCmd=sMsg+sNewCmd

    #Configuración de página y estilos
    sEst=self.pageConfig()+'\n'
    sEst+=self.pageStyle()+'\n'
    
    #Una vez se conocen todos los paquetes requeridos
    #se inicia a escribir el preámbulo
    documentclass=LatexCommand('documentclass','',1)
    opt=''
    if self._cfg_fontsize !=None:
      opt+=self._cfg_fontsize
    if self._cfg_paper !=None:
      if len(opt)> 0:
        opt+=','
      opt+=self._cfg_paper

    if self._cfg_language != 'english' or self._cfg_language != None:
      opt+=','+self._cfg_language
    s=documentclass( (opt,),self._cfg_docclass)+'\n'
    #%%%%%%%%%%%%%%%%%
    #Paquetes
    if self._cfg_language != 'english':
      self._packs['babel']=PACKAGES['babel']
      self._packs['babel'].setOptions('english,'+self._cfg_language)
      self._packs['inputenc']=PACKAGES['inputenc']
      self._packs['inputenc'].setOptions('utf8')
    
    ltPacks=[v for k,v in self._packs.items()]
    ltPacks.sort()
    for pack in ltPacks:
      if pack.name =='graphicx':
        s+=pack()
        s+='\\graphicspath{{%s}}\n'%self._cfg_tree['figures']
      elif pack.name == 'geometry':
        pass
      else:
        s+=pack()
        
    #Agrega las configuraciones de página y estilos
    s+=sEst
    #Agrega las redefiniciones y nuevas definiciones
    s+=sRenewCmd+sNewCmd
    s+=self._sEndPreamble
    self._spreamble=s
    return s



  def appendPreamble(self,s):
    '''
    Agrega al final de preámbulo
    '''
    self._sEndPreamble+=s


  def setDocIni(self,s):
    '''
    Agrega un contenido al inicio de 
    begin document, antes de que se empiece
    a agregar más contenidos. Por ejemplo el 
    makeTitle, etc.
    '''
    self.__docIni=s
  #%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  def genDoc(self, target=False,clean=True):
    '''
    Genera el documento latex utilizando un makefile, el cual si:
    * target es False compilará todo archivo tex, en caso contrario, únicamente
      el que corresponde al actual documento
    * clean si es true se borrarán los logs y archivos auxialeres al final 
      de la compilación
    
    En los casos en que exista necesidad de compilar dos veces, por ejemplo 
    cuando se utilizan enlaces, o referencias, se debe utilizar en 
    la primera vez de compilación clean=False, y en la segunda clean=True.
    
    Si se quiere compilar externamente, para compilar sin borrar se utiliza 
    $ make compila
    
    y para el caso de querer compilar eliminando los archivos auxiliares
    $ make compilayborra
    '''
    # siempre se genera el makefile
    # porque se puede cambiar el nombre del archivo
    # y quedaría compilando otro archivo
    if isinstance(target,bool):
      if target:
        target= self._name
        if not ( target.split(".")[-1]=='tex'):
          target+=".tex"
      else:
        target='*.tex'

    dirOut=self._dirOut
    makefiledir= os.path.join(dirOut,'Makefile')
    with open(makefiledir,'w') as f:
      f.write(self._makefile(target,clean))
    
    #obtiene el nombre y directorio donde 
    # se genera la salida
    try:
      #Ejecuta make sobre el directorio especificado
      s=subprocess.check_output("make -C " +
       dirOut,shell=True,stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
      #Si se genera un error se imprime la información
      raise RuntimeError(
        "command '{}' return with error (code {}): {}".format(
          e.cmd, e.returncode, e.output.decode('utf8')
        )
      )
  

