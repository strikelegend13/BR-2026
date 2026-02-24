# simple web server for yourself
# import socket module
from socket import *
# In order to terminate the program
import sys

def webServer(port=13331):
  serverSocket = socket(AF_INET, SOCK_STREAM)
  #Prepare a server socket
  serverSocket.bind(("", port))
  serverSocket.listen(1)
  while True:
    #Establish the connection
    print('Ready to serve...')
    connectionSocket, addr = serverSocket.accept()
    try:
      message = connectionSocket.recv(1024).decode()
      filename = message.split()[1]
      #opens the client requested file. 
      f = open(filename[1:], 'rb')
      header = b"HTTP/1.1 200 OK\r\nServer: helloworld.html Server\r\n"
      outputdata = header + b"Content-Type: text/html; charset=UTF-8\r\n"
      content = b""
      #Content-Type is an example on how to send a header as bytes. There are more!
      #Note that a complete header must end with a blank line, creating the four-byte sequence "\r\n\r\n" Refer to https://w3.cs.jmu.edu/kirkpams/OpenCSF/Books/csf/html/TCPSockets.html
      #Fill in end
      for i in f: #for line in file
        content += i
      f.close()
      #Send the content of the requested file to the client (don't forget the headers you created)!
      #Send everything as one send command, do not send one line/item at a time
      response = outputdata + f"Content-Length: {len(content)}\r\n".encode() + b"Connection: close\r\n\r\n" + content
      connectionSocket.sendall(response)
        
      connectionSocket.close() #closing the connection socket
      
    except Exception as e:
      # Send response message for invalid request due to the file not being found (404)
      # Remember the format you used in the try: block!
      error = b"<html><body><h1>404 Not Found</h1></body></html>"
      errorback = (
        b"HTTP/1.1 404 Not Found\r\n"
        b"Server: helloworld.html Server\r\n"
        b"Content-Type: text/html; charset=UTF-8\r\n"
        + f"Content-Length: {len(error)}\r\n".encode()
        + b"Connection: close\r\n\r\n"
        + error
      )
      connectionSocket.sendall(errorback)


      #Close client socket
      connectionSocket.close()
  # Commenting out the below (some use it for local testing). It is not required for Gradescope, and some students have moved it erroneously in the While loop. 
  # DO NOT PLACE ANYWHERE ELSE AND DO NOT UNCOMMENT WHEN SUBMITTING, YOU ARE GONNA HAVE A BAD TIME
  #serverSocket.close()
  #sys.exit()  # Terminate the program after sending the corresponding data

if __name__ == "__main__":

  webServer(13331)

