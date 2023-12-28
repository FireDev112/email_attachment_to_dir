from FetchEmail import FetchEmail as fe
from dotenv import load_dotenv
import os
import time
import shutil
import mariadb


class EmailAttachmentHandler():
    # Umgebungsvariablen setzen
    load_dotenv()

    def __init__(self) -> None:
        # Mailadressenzugang
        self.mail_adresse = str(os.getenv("EMAIL_ADR"))
        self.mail_pwd     = str(os.getenv("EMAIL_PWD"))
        self.mail_server  = str(os.getenv("EMAIL_SERVER"))
        self.mail_port    = str(os.getenv("EMAIL_PORT"))

        # Temp Ordner
        self.temp_dir = str(os.getenv("TEMP_DIR"))

        # Datenbank Zugangsdaten
        self.maria_db_user       = str(os.getenv("MARIA_DB_USER"))
        self.maria_db_pwd        = str(os.getenv("MARIA_DB_PWD"))
        self.maria_db_table      = str(os.getenv("MARIA_DB_TABLE_FOR_NEW_ALARMS"))
        self.maria_db_table_mail = str(os.getenv("MARIA_DB_TABLE_FOR_NEW_MAIL_ATTACHMENT"))
        self.maria_db_database   = str(os.getenv("MARIA_DB_DATABASE"))
        self.maria_db_ip         = str(os.getenv("MARIA_DB_IP"))
        self.maria_db_port       = int(os.getenv("MARIA_DB_PORT"))
        # Konstanten
        self.INVALID_PATH = "PATH_NOT_FOUND"
    
    def check_new_mails(self):
        try:
            # Neue Verbindung herstellen
            conn = fe(self.mail_server, self.mail_adresse, self.mail_pwd)
            list_of_new_msg = conn.fetch_unread_messages()
            if len(list_of_new_msg) > 0:
                print(f"Es sind {len(list_of_new_msg)} neue Nachrichten im Mailpostfach!")
                # Alle Elemente in den /tmp Ordner speichern
                for mail in list_of_new_msg:
                    conn.save_attachment(mail)

            # Verbindung beenden
            conn.close_connection()
        except Exception as e:
            print(f"Es konnte keine Verbindung mit dem Mailserver hergestellt werden {e}")
    
    def copy_attachment_to_alarm_dir(self):
        # Im Ordner nach Dateien suchen
        try:
            list_of_temp_dir = os.listdir(self.temp_dir)
            if len(list_of_temp_dir) > 0:
                # Durch Liste der Anhänge iterieren
                for element in list_of_temp_dir:
                    klst_nr, attachment_type = self.get_klst_nr_and_type_from_attachment(element)
                    if klst_nr != "KLST_NR_NOT_FOUND":
                        dir_path_tuple = self.get_path_from_klst_nr(klst_nr)
                        if dir_path_tuple != self.INVALID_PATH :
                            # Convert from Tuple to str
                            dir_path = dir_path_tuple[0]
                            # /Einsatzberichte/2023/20231227_097973__Friedenstraße_27_Testeinsatz
                            # Namensstruktur herausfinden und neuen Name
                            dir_name = self.INVALID_PATH
                            try:
                                dir_name =  dir_path.split('/')[-1]
                            except Exception as e:
                                print(f"Fehler beim dir Namen{type(dir_path)} {dir_path}: {e}")
                            attachment_type_file = ".pdf"
                            try:
                                attachment_type_file =  element.split('.')[-1]
                            except Exception as e:
                                print(f"Fehler beim Dateityp {type(attachment_type_file)} {attachment_type_file}: {e}")

                            new_name = f"{dir_name}_{attachment_type}.{attachment_type_file}"
                            new_path = os.path.join(dir_path, new_name)
                            print(f"Neuer Pfad für {element}: {new_path}")
                            src_path = os.path.join(self.temp_dir, element)
                            print(src_path)
                            try: 
                                shutil.move(src_path, new_path)
                            except Exception as e:
                                print(f"Datei konnte nicht kopiert werden: {e}")
                                print(f"Src: {src_path}, Dst: {new_path}")
                        else:
                            print(f"Kein Pfad in DB gefunden! {klst_nr}")
                            continue
                    else:
                        print(f"Keine KLST NR in Element Namen gefunden: {element}")
                        continue
        except Exception as e:
            print(f"Fehler beim Öffnen des Verzeichnisses: {self.temp_dir}: {e}")
        pass

    def get_klst_nr_and_type_from_attachment(self, attachment_name):
        klst_nr="KLST_NR_NOT_FOUND"
        attachment_type="TYPE_NOT_FOUND"
        try:
            # Unterscheiden in Alarmdepeche und Einsatzabschlussbericht
            if "Alarmdepeche" in attachment_name:
                attachment_type = "Alarmdepesche"
                # Alarmdepeche__anhang_01.2023.097976.11559.full.pdf
                klst_nr = attachment_name.split(".")[2]
            elif "Abschlussbericht" in attachment_name:
                attachment_type = "Abschlussbericht"
                # Abschlussbericht__anhang_97730.25410.2023
                klst_nr = attachment_name.split(".")[0].split("_")[-1]
            else:
                pass #Nop
        
        except Exception as e:
            print(f"Fehler beim ermiitelnm der KLST Nr: {attachment_name}  {e}")

        return klst_nr, attachment_type
            
    
    def get_path_from_klst_nr(self, klst_nr):
         # Connect to MariaDB Platform
        path_to_dir_=self.INVALID_PATH
        try:
            conn = mariadb.connect(
                user=self.maria_db_user,
                password=self.maria_db_pwd,
                host=self.maria_db_ip,
                port=self.maria_db_port,
                database=self.maria_db_database
            )
            print("Erfolgreich mit der DB Verbunden ")
            # Get Cursor
            cur = conn.cursor()
            # Versuchen Daten aus DB zuholen
            try: 
                sql_expr = f'SELECT PATH_TO_DIR FROM {self.maria_db_database}.{self.maria_db_table} WHERE LST_NR LIKE "%{klst_nr}"'
                print(f"SQL_EXPR: {sql_expr}")
                cur.execute(sql_expr)
                sql_answer = None
                for PATH_TO_DIR in cur:
                    sql_answer = PATH_TO_DIR
                    break
                if sql_answer != None:
                    print(f"Eintrag zu {klst_nr} in DB gefunden! Pfad: {sql_answer}")
                    path_to_dir_ = sql_answer
                else: 
                    print(f"Kein Eintrag in der DB für {klst_nr} ")

            except Exception as e:
                print(f"Fehler im SQL Expr: {e}")
            
            # Daten an Datenbank übertragen
            try:
                conn.commit()
            except:
                print(f"Es konnten keine Daten in die DB geschrieben werden!: {e}")

            # Von der DB abmelden
            conn.close()

        except mariadb.Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
        
        return path_to_dir_
    

    def run(self):
        # infinite Loop
        print(f"E-Mail Fetcher gestartet")
        print("Starte Main Loop")
        while True:
            # 1. Neue Emails abrufen
            self.check_new_mails()
            # 2. Anhang kopieren
            self.copy_attachment_to_alarm_dir()
            # Schlafen
            time.sleep(30.0)



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    connector = EmailAttachmentHandler()
    connector.run()