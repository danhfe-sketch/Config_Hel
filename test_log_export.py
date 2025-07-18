import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import datetime
from collections import deque

# Add the project root to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create a mock version of the LogFrame class g
class MockLogFrame:
    def __init__(self, master, i18n, svice):
        self.master = master
i18n
        self.serial_service = serial_sevice
        self.log_entries = deque(maxlen=1000
()
        self.log_buf []
        
    def log_message(self, mes):
        """Mock implementation of
        timestamp = datetime.da
        self.log_entries.append((timestamp, message))
        
    def format_log_for_export(self, log_cont):
        """
        Format the log content for export w.
        T.
        """
        lines = log_content.split('\n')
        formatted_lines = []
        
        # Usilable
        if self.log_entries:
            for timestamp, message in self.
                if not message.strip():
                    continue
                
                # Extract category from the message
                if message.startswith("APP:"):
        PP"
                    content ()
                elif message.startswith("DEV:"):
                    category = "DEV"
                    content = message[4:].strip()
                elif message.startswith("INFO:"):
        NFO"
                    content = message[5:].strip()
                elif message.startswith("ERR"):
                    category = "ERROR"
                    content = message[6:].sp()
                elif message.startswith("WARNING:"):
                    category = "WARNING"
        trip()
                elif message.startswith("DEBUG:"):
                    category = 
                    content = message[6:].strip()
           else:
                    category = "SYST
                    content = messae.strip()
        
                # Format with full date and time
                full_timestamp = f"{datetime."
        "
                formatted_lines.append(formatted_lin
        else:
        ailable
            current_time = datetime.datetime.now()
            
        
                if not line.strip():
                    continue
                
                # Extract category from the formatted log line
                category = "APP"  # Defaulory
        trip()
                
                # Add timestamp to e
        ")
                
                # Format the line with timestry
        
                formatted_lines.append(formatted_line)
                
        tries
                current_time += datetime.nds=100)
        
        return '\n'.join(formats)
    
    def 
        """Mock implementation of export_log."""
        from tkinter import filedialog
        
        # Get the log content
        -1c")
        if not log_content:
            self.log_message("WARNING: No log content to export\n")
        rn
        
        # Format the log content with timeon
        formatted_log = self.format_log_for_export(log_content)
        
        # Open file dialog to select save location
        default_filename = f"LT32Pro_Log_{datxt"
        file_path = filedialog.asksaveasfilen(
            defaultextension=".txt",
        
            title=self.i18n.get("export_log"),
            initialfile=default_filename
        )
        
        if not file_path:
            return  # User cancelled the dialog
        
        try:
            with open(file_path, 'w', encoding='utf-8' as f:
        
                current_time = datetime.datetime.n")
                f.write(f"LT32Pro Device Configurator - Log
        \n")
                
                # Add device informle
        :
                    if self.serial_service.devic
                        f.write(f"Device IMEI: {self.serial_service.device_info['imei']}\n")
        
                        f.write(f"Den")
                
                f.write("-" * 50 + "\n\n")
                
        nt
                f.write(formatted_log)
            
        e
            self.log_message(f"INFO: Log exported)
            

            # Log error mee
            self.lotest.main()    unitn__':
= '__mai__ =if __name")

t\nto exporcontent g  No loRNING:d_with("WAert_calleage.assg_messme.loelf.log_fra  s    ed
  was loggng message that a warniheck  # C
       )
        g(rt_loexpog_frame.f.lo   sel    
 log methodexport_# Call the        
        
 lue="")vaturn_ck(reicMo.get = Magboxxte.log_telog_fram       self.y string
  emptan return textbox to the log_    # Mock
    g.""" empty loexporting an """Test ):
       _log(selftyempport_test_ex   def  
 
       on\n")st exceptit log: Teexpor to R: Failed("ERROlled_witht_caser_message.asframe.logself.log_   
      loggedsage wasrror mesthat an eheck # C
            log()
    ame.export_elf.log_fr     sod
   ethort_log mCall the exp #     
         ion")
   except"Testception(ect = Exe_effn.sidock_ope        m exception
 to raise an openleMock the fi  #     
      txt"
    st_log. = "teturn_valuelog.re_diaave_s  mockh
      at pileturn a f reialog toe file dthock  M"
        #""ort.expog ons during lti excepingt handlTes" "":
       _dialog)ock_save_open, melf, mockption(s_excet_log_withf test_expor  de=True)
  en', createiltins.opbuatch('   @p
 asfilename')g.asksave.filedialoch('tkinterpat  
    @     {2}\]")
 2}:\d}:\d{{2} \d{2{2}-\d}-\d\[\d{4 r"atted_log,ormssertRegex(f     self.aed
   ncludps are ihat timestamCheck t        #    
og)
     _l, formattedAPP]"assertIn("[self.        egories
atd ctehe expecs tintall contied log sormatthat the f   # Check t      
  
     tbox.get())exme.log_tg_fra(self.lo_for_exportat_log.formlf.log_framelog = seormatted_
        f()lear_entries.cog_frame.log     self.l
    entriesogithout l wst    # Te      
    ")
  }\]\d{2}:\d{2} \d{2}:{2\d}--\d{2r"\[\d{4}_log, rmattedtRegex(foser.as   self
     ncludedre is aat timestamp th # Check 
           g)
   ted_lo format]",tIn("[ERRORelf.asser
        sted_log) formatV]","[DEertIn( self.ass    ed_log)
   , formatt"[APP]"f.assertIn(    selies
     categore expectedtains thted log conformatck that the      # Che   
        ")
_export("og_format_lore.f_framelf.logg = sormatted_lo  fs
      log entrieh Test wit
        # ""port."for extent ting log conmatTest for"     ""  
 :xport(self)_for_eformat_log test_ef   d
       called()
  assert_not_e.essaglog_mf.log_frame.  sel     d
 e was loggeror messag erccess oro suk that n     # Chec
           once()
led_cal.assert_save_dialog     mock_
   was calledog e file dialthat th# Check          
      log()
 ort_e.expframog_ self.l
       g method_lo the export   # Call           
  ""
alue = urn_v_dialog.retmock_save        ancelled)
er crn None (usto retuog  file dial # Mock the
       og."""alg dirt loing the expoancellest c"""T        log):
e_dia, mock_savncel(self_caort_logf test_expde
    filename')sksaveasiledialog.aer.fnt@patch('tki   
    \n")
     txto test_log.cessfully tted sucg exporLo(f"INFO: withed_sert_callssage.aslog_meme.ra self.log_f
       edge was loggessasuccess mhat a k t  # Chec   
      )
     tf-8' encoding='u'w',g.txt", est_lonce_with("td_ole.assert_calpenck_o      mo writing
  opened fore file was hat theck t # Ch      
  
       once()rt_called_og.asseialsave_d    mock_d
     was callealog file dick that the # Che      
        
 ()e.export_log.log_framlf
        se_log methodhe export   # Call t        
file
     ock_n_value = m__.returter.__enreturn_value_open.ock     m  ()
 MagicMockock_file =      mons
   eratirite ope open and w the fil    # Mock   
    t"
     .tx "test_log_value =ialog.returne_d    mock_save path
    urn a filret dialog to ock the file # M"
       ""le.fi a ting log tot expor"""Tes :
       dialog)save_k_n, moc_ope, mocklfrt_log(seexpodef test_ue)
    ', create=Trenins.opbuilt  @patch('lename')
  asfisave.askdialog.filetch('tkinter    @pa      
e"))
  ssagOR: Error meERRmestamp, "append((tig_entries.me.lof.log_fra       sel
 se"))esponevice r "DEV: Damp,d((timestppen.alog_entries.log_frame.   self))
     essage": Test mmp, "APPd((timestaries.appen.log_entf.log_frame     sel
   )S"me("%H:%M:%).strftiow(etime.natetime.d= datstamp     time   entries
 et up log  # S
           )
    or message"n[ERROR] Errnse\ce respo Devin[DEV]t message\"[APP] Tes_value=urnicMock(ret= Magx.get log_textbog_frame.loself.     ck()
   MagicMosage = ame.log_mesfrlog_self.        ce)
l_servi.seriaf.i18n, selfelster, self.maFrame(sckLoge = Moramg_f    self.lo    nstance
Frame ik LogmocCreate a 
        #       }
        '
  4321065876543210987'iccid': '9            012345',
123456789 '':    'imei       {
 vice_info = vice.deal_ser self.serik()
        = MagicMocal_servicef.seri  sel     ")
 port Logalue="Exturn_vock(reMagicM.i18n.get =     self   Mock()
 Magicself.i18n = )
        agicMock(er = M   self.mastcts
      mock obje # Create"
       nment.""irotest env"Set up the   ""
      self):etUp( def s
   y."""
itfunctional export Test the log   """stCase):
 ittest.Tet(unxporestLogEs T()

clasckMagicMo'] = edialoginter.filtk['modules
sys.k()icMoc = Magpyperclip']les['()
sys.moduMagicMock = tomtkinter']uss['c
sys.moduletestsin e issues t caus modules tha)

# Mockstr(e)}\n"log: {port led to exai Fe(f"ERROR:sagg_mes