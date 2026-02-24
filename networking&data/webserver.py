# simple web server for yourself, crafted through edited code from Kurose Top-Down Approach Networking .
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
      for i in f: #for line in file
        content += i
      f.close()
      response = outputdata + f"Content-Length: {len(content)}\r\n".encode() + b"Connection: close\r\n\r\n" + content
      connectionSocket.sendall(response)
        
      connectionSocket.close() #closing the connection socket
      
    except Exception as e:
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


      connectionSocket.close()

  #serverSocket.close()
  #sys.exit()  # Terminate the program after sending the corresponding data

if __name__ == "__main__":

  webServer(13331)



