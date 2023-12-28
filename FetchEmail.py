import email
import imaplib
import os

class FetchEmail():

    connection = None
    error = None

    def __init__(self, mail_server, username, password):
        self.connection = imaplib.IMAP4_SSL(mail_server)
        self.connection.login(username, password)
        self.connection.select(readonly=False) # so we can mark mails as read
        self.list_with_corr_mail_adresses = ["kreisleitstelle@kreis-steinfurt.de", "depeschen@feuerwehr-neuenkirchen.de", "depeschendrucker@feuerwehr-neuenkirchen.de"]

    def close_connection(self):
        """
        Close the connection to the IMAP server
        """
        self.connection.close()

    def save_attachment(self, msg, download_folder="./tmp"):
        """
        Given a message, save its attachments to the specified
        download folder (default is /tmp)

        return: file path to attachment
        """
        subject = "Subject_not_found"
        # Get Subject
        for element in msg._headers:
            if element[0] == 'Subject':
                try:
                    subject = element[1]
                except Exception as e:
                    print(f"Betreff konnte nicht ausgelesen werden: {e}")

        # Typ des Anhangs prüfen
        if "Alarmdepeche" in subject:
            type_of_message = "Alarmdepeche"
        else:
            type_of_message = "Abschlussbericht"


        att_path = "No attachment found."
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue
            if part.get('Subject') is not None:
                subject = part.get('Subject')
                print(subject)
    

            filename = part.get_filename()
            filename = f"{type_of_message}__{filename}"
            att_path = os.path.join(download_folder, filename)

            if not os.path.isfile(att_path):
                fp = open(att_path, 'wb')
                fp.write(part.get_payload(decode=True))
                fp.close()
        return att_path

    def fetch_unread_messages(self):
        """
        Retrieve unread messages
        """
        emails = []
        (result, messages) = self.connection.search(None, 'UnSeen')
        if result == "OK":
            for message in messages[0].split():
                try: 
                    ret, data = self.connection.fetch(message,'(RFC822)')
                except:
                    print ("No new emails to read.")
                    self.close_connection()
                    exit()

                msg = email.message_from_bytes(data[0][1])
                if isinstance(msg, str) == False:
                    # Prüfen ob die Mail vom korrekten absender kommt
                    if  self.check_if_correct_sender(msg):
                        emails.append(msg)
                response, data = self.connection.store(message, '+FLAGS','\\Seen')

            return emails

        self.error = "Failed to retreive emails."
        return emails
    
    def check_if_correct_sender(self, msg):
        for element in msg._headers:
            if element[0] == 'From':
                try:
                    sender_mail = element[1].split('"')[1]
                    if  sender_mail in self.list_with_corr_mail_adresses:
                        return True
                    else:
                        return False
                except Exception as e:
                    print(f"Absender konnte nicht ausgelesen werden: {e}")


    def parse_email_address(self, email_address):
        """
        Helper function to parse out the email address from the message

        return: tuple (name, address). Eg. ('John Doe', 'jdoe@example.com')
        """
        return email.utils.parseaddr(email_address)