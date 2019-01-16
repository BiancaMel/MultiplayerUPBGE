import socket
import threading
import time
import bge
import select
import zlib

class ClientMP():
    def __init__(self, MpManager, PlayerObject, ServerHost, ClientIP):
        self.MpManager = MpManager
        self.ClientHost = (ClientIP, 0)
        self.ServerHost = ServerHost
        self.player = PlayerObject
        self.ClientComponent = self.player.components['Client']
        self.sendData = {}
        self.receivedData = None
        self.playersList = []
        self.playersIDs = []
        self.connected = False
        self.data, self.address = None, None
        self.UpdateTime = 0.1
        self.refreshTime = time.clock()
        self.timer = time.clock() - self.refreshTime
        self.Ping = 0.0
        self.LastTime = time.clock()
        self.Port = 0
        self.CanTryConnect = True
        self.sendData["Connected"] = 1
        self.sendData["Action"] = {}
        self.waitMessages = {}
        self.Local = ""
        self.SubLocal = ""
        self.TimeOut = 5.0

        self.ResponseRefreshTime = time.clock()
        self.ResponseTimer = time.clock() - self.ResponseRefreshTime
        self.LastMsg = None
        #self.RoomsList = {}

        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(self.ClientHost)
            self.sock.setblocking(0)
            self.sock.settimeout(self.TimeOut)
            self.ClientHost = self.sock.getsockname()
            print("Connecting...")
            
        except:
            print("Error on trying to connect to server!")


    def Update(self):
        self.timer = time.clock() - self.refreshTime
        self.ResponseTimer = time.clock() - self.ResponseRefreshTime
        if self.CanTryConnect:
            #try:
                read_sockets, write_sockets, error_sockets = select.select([self.sock] , [], [], 0.0)

                if read_sockets:
                    self.data, self.address = self.sock.recvfrom(8192)
                    self.ResponseRefreshTime = time.clock()


                    self.receivedData = eval(zlib.decompress(self.data).decode("ascii"))
                    #self.receivedData = eval(self.data.decode("ascii"))
                    #print("Data: ", self.receivedData)
                    if self.receivedData['Your']["Connected"] == 1:
                        self.ClientComponent.ID = self.receivedData['Your']["ID"]
                        if self.receivedData['Your']['Local']["Name"] != "Loggin":
                            if not self.receivedData['Your']["ID"] in self.playersIDs:
                                self.playersIDs.append(self.receivedData['Your']["ID"])
                    
                            if self.receivedData['Your']['Msg'] != None:
                                self.OnReceivedMessage()
                            

                            if self.Local != self.receivedData['Your']['Local']:
                                self.Local = self.receivedData['Your']['Local']
                                self.OnChangedLocal()
                            if self.SubLocal != self.receivedData['Your']['SubLocal']:
                                self.SubLocal = self.receivedData['Your']['SubLocal']
                                self.OnChangedSubLocal()

                            if self.receivedData["Players"] != None:
                                self.Ping = float(self.receivedData['Players'][self.receivedData['Your']["ID"]]['Ping'])#+self.ResponseTimer

                            self.UpdatePlayers()
                        #elif self.receivedData['Your']['Local']["Name"] == "Loggin":
                        #    pass
                    
                        if not self.connected:
                            self.connected = True
                            print("Connected!")
                    else:
                        self.CanTryConnect = False
                        self.connected = False
                        self.sock.close()
                        self.OnDisconnect()
                elif self.ResponseTimer > self.TimeOut:
                    print("TimeOut")
                    self.OnLostConnection()
                try:
                    if self.timer > self.UpdateTime:
                        self.refreshTime = time.clock()
                        #self.sock.sendto((str(self.sendData).encode("ascii")), self.ServerHost)
                        self.sock.sendto(zlib.compress(str(self.sendData).encode("ascii")), self.ServerHost)
                        #self.sendData["Action"] = {}
                except:
                    pass
                    
            #except:
                #print("Erro")
            #    self.OnLostConnection()

    def OnChangedLocal(self):
        pass

    def OnChangedSubLocal(self):
        pass
    
    def OnReceivedMessage(self):
        print("Msg:", self.receivedData['Your']['Msg'])
        self.sendData["Action"] = {}

    def UpdatePlayers(self):
        for item in self.receivedData["Players"]:
            if item != self.ClientComponent.ID:
                if not item in self.playersIDs:
                    self.playersIDs.append(item)
                    PlayerOBJ = self.MpManager.scene.addObject(self.player.name)
                    PlayerOBJ.components["Client"].ID = item
                    self.playersList.append(PlayerOBJ)
        for player in self.playersList:
            if not player.components["Client"].ID in self.receivedData["Players"]:
                player.components["Client"].DeletePlayer()
                self.playersList.remove(player)
                self.playersIDs.remove(player.components["Client"].ID)
                player.endObject()

    def OnDisconnect(self):
        print("Disconnected.")

    def OnLostConnection(self):
        self.sendData['Connected'] = 0
        self.CanTryConnect = False
        if self.connected:
            self.connected = False
        self.sock.close()
        print("Lost Connection!")

    def SendAction(self, ActionDict, CallOnReceive=None):
        self.sendData["Action"][ActionDict["Name"]] = ActionDict
        self.sock.sendto(zlib.compress(str(self.sendData).encode("ascii")), self.ServerHost)
        self.waitMessages[ActionDict["Name"]] = {"CallOnReceive": CallOnReceive}

    def Disconnect(self):
        #self.connected = False
        self.sendData['Connected'] = 0
        #self.sock.sendto(str(self.sendData).encode("ascii"), self.ServerHost)

        #self.sock.close()
        #print("Disconnected!")

