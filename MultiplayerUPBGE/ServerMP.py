import socket
import time
import threading
import select
import atexit
import random
import numpy
import zlib

class Server():
    def __init__(self):
        print("Server Started, running...")
        print("type 'q' or 'quit' to exit correctly.")

        #self.host = "25.56.194.119"
        self.host = ("localhost", 7015)
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSock.bind(self.host)

        self.data, self.address = None, None
        self.LobbyDataToSend = {}
        self.idList = []
        self.RoomsList = {}
        self.AddressList = {}
        self.receivedData = None
        self.Work = True
        self.TimeOut = 5.0
        
        self.inputThread = threading.Thread(target=self.ExecCommand)
        self.inputThread.start()
        atexit.register(self.Quit)

        self.Main()


    def Main(self):
        while self.Work:
            try:
                read_sockets, write_sockets, error_sockets = select.select([self.serverSock] , [], [], 0.0)
                #print(read_sockets, write_sockets, error_sockets)
                #self.CheckTimeOut()

                if read_sockets:
                    self.data, self.address = self.serverSock.recvfrom(8192)
                    #self.receivedData = eval(self.data.decode("ascii"))
                    self.receivedData = eval(zlib.decompress(self.data).decode("ascii"))
                    #print("ReceivedData: ", self.receivedData)

                    self.SendPlayerData()
            except:
                pass
            #print("DataToSend: ", self.LobbyDataToSend)
            #time.sleep(0.039)
    def GetNumberOfPlayersInRoom(self, RoomID):
        self.RoomsList[RoomID]["Info"]["PlayersIn"] = len(self.RoomsList[RoomID]["Players"])

    def GetAllRoomsInfo(self):
        RoomsInfo = {}
        for room in self.RoomsList:
            RoomsInfo[room] = self.RoomsList[room]["Info"]
        
        return RoomsInfo

    def CreateRoom(self, address, YourDict):
        if self.AddressList[self.address]['Local']['Name'] == "Lobby":
            newID = 0
            while newID in self.RoomsList:
                newID += 1
            self.RoomsList[newID] = {"Info": {"ID": newID, "Owner": self.AddressList[address]['ID'], "Name": "Room", "PlayersIn": 0, "MaxPlayers": 2}, "Players": {}}
            self.MovePlayerToRoom(address, newID, YourDict)
        else:
            YourDict["Msg"]["Ok"] = {"Name": "Ok", "Data": None}

    def EnterAnyRoom(self, address, YourDict):
        roomKeys = list(self.RoomsList.keys())
        if roomKeys:
            self.MovePlayerToRoom(address, random.choice(roomKeys), YourDict)
        else:
            YourDict["Msg"]["NoneRooms"] = {"Name": "NoneRooms", "Data": None}

    def OnPlayerLeftRoom(self, RoomID):
        if not self.RoomsList[RoomID]["Players"]:
            del(self.RoomsList[RoomID])
        else:
            self.GetNumberOfPlayersInRoom(RoomID)
            if not self.RoomsList[RoomID]["Info"]["Owner"] in self.RoomsList[RoomID]["Players"]:
                newOwner = random.choice(list(self.RoomsList[RoomID]["Players"].keys()))
                self.RoomsList[RoomID]["Info"]["Owner"] = newOwner

    def ChangeRoomMaxPlayers(self, PlayerAddress, YourDict, Number):
        if self.AddressList[PlayerAddress]['Local']['Name'] == "Room":
            if self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Info"]["Owner"] == self.AddressList[PlayerAddress]["ID"]:
                self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Info"]["MaxPlayers"] = int(numpy.clip(Number, len(self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Players"]), 16))
                YourDict["Msg"]["ChangedMaxPlayers"] = {"Name": "ChangedMaxPlayers", "Data": None}
            else:
                YourDict["Msg"]["Ok"] = {"Name": "Ok", "Data": None}
        else:
            YourDict["Msg"]["Ok"] = {"Name": "Ok", "Data": None}
    
    def MovePlayerToRoom(self, PlayerAddress, RoomID, YourDict=None):
        if RoomID in self.RoomsList:
            if self.AddressList[PlayerAddress]['Local']['Name'] == "Lobby":
                if self.RoomsList[RoomID]["Info"]["PlayersIn"] < self.RoomsList[RoomID]["Info"]["MaxPlayers"]:
                    del(self.LobbyDataToSend[self.AddressList[PlayerAddress]['ID']])
                    self.AddressList[PlayerAddress]['Local']['Name'] = "Room"
                    self.AddressList[PlayerAddress]['Local']['Data'] = self.RoomsList[RoomID]["Info"]
                    self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Players"][self.AddressList[PlayerAddress]['ID']] = self.SendDict()
                    self.GetNumberOfPlayersInRoom(RoomID)
                    YourDict["Msg"][""] = {"Name": "EnteredInRoom", "Data": None}
                elif YourDict != None:
                    YourDict["Msg"]["FullRoom"] = {"Name": "FullRoom", "Data": None}
            else:
                YourDict["Msg"]["Ok"] = {"Name": "Ok", "Data": None}
        else:
            YourDict["Msg"]["NonExistRoom"] = {"Name": "NonExistRoom", "Data": None}

    def MovePlayerToLobby(self, PlayerAddress, YourDict):
        if self.AddressList[PlayerAddress]['Local']['Name'] == "Room":
            del(self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Players"][self.AddressList[PlayerAddress]['ID']])
            self.OnPlayerLeftRoom(self.AddressList[PlayerAddress]['Local']['Data']["ID"])
        else:
            YourDict["Msg"]["Ok"] = {"Name": "Ok", "Data": None}
        self.AddressList[PlayerAddress]['Local']['Name'] = "Lobby"
        self.AddressList[PlayerAddress]['Local']['Data'] = 0
        self.LobbyDataToSend[self.AddressList[PlayerAddress]['ID']] = self.SendDict()
        YourDict["Msg"]["MovedToLobby"] = {"Name": "MovedToLobby", "Data": None}

    def Update(self):
        pass

    def SendDict(self, Flag=None):
        SendDictData = {'Ping': "{0:.4f}".format(self.AddressList[self.address]['Ping'])}
        return SendDictData
    
    def ExecPlayerActions(self, Address):
        YourDict = {'ID': self.AddressList[Address]['ID'],
                    "Connected": 1,
                    "Msg": {},
                    "Local": self.AddressList[Address]['Local'],
                    "SubLocal": self.AddressList[Address]['SubLocal']
                    }
        if self.receivedData['Action'] != None:
            for act in self.receivedData['Action']:
                if act["Name"] == "GetRoomsList":
                    YourDict['Rooms'] = self.GetAllRoomsInfo()
                    YourDict["Msg"]["RoomsList"] = {"Name": "RoomsList", "Data": None}
                elif act["Name"] == "CreateRoom":
                    self.CreateRoom(Address, YourDict)
                elif act["Name"] == "EnterAnyRoom":
                    self.EnterAnyRoom(Address, YourDict)
                elif act["Name"] == "QuitToLobby":
                    self.MovePlayerToLobby(Address, YourDict)
                elif act["Name"] == "ChangeRoomMaxPlayers":
                    self.ChangeRoomMaxPlayers(Address, YourDict, act["Data"])
        
        return YourDict


    def OnEnterNewPlayer(self, Address, newID):
        self.AddressList[Address] = {}
        self.AddressList[Address]["Received"] = self.receivedData
        self.AddressList[Address]['ID'] = newID
        self.AddressList[Address]['Ping'] = 0.0
        self.AddressList[Address]['Timeout'] = 0.0
        self.AddressList[Address]['Local'] = {"Name": "Loggin", "Data": 0}
        self.AddressList[Address]['SubLocal'] = {"Name": None, "Data": None}
        self.AddressList[Address]['Logged'] = False

        print("ID ", newID," connected.")

    def SendPlayerData(self):
        if self.receivedData['Connected'] == 0:
            self.RemovePlayer(self.address)
            #pass
        else:
            if not self.address in self.AddressList:
                newID = 0
                while newID in self.idList: 
                    newID += 1
                self.idList.append(newID)
                self.OnEnterNewPlayer(self.address, newID)


            self.AddressList[self.address]["Received"] = self.receivedData
            self.AddressList[self.address]['Ping'] = time.clock() - self.AddressList[self.address]['Timeout']
            self.AddressList[self.address]['Timeout'] = time.clock()
            

            YourDict = self.ExecPlayerActions(self.address)
            DataToSend = self.GetDataFromLocal()
            
            #self.serverSock.sendto(str({"Your": YourDict, "Players": DataToSend}).encode("ascii"), self.address)
            self.serverSock.sendto(zlib.compress(str({"Your": YourDict, "Players": DataToSend}).encode("ascii")), self.address)

    def RemovePlayer(self, PlayerAddress):
        try:
            #pass
            #self.serverSock.sendto(str({"Your": {'ID': self.AddressList[PlayerAddress]['ID'], "Connected": 0}, "Players": self.LobbyDataToSend}).encode("ascii"), PlayerAddress)
            self.serverSock.sendto(zlib.compress(str({"Your": {'ID': self.AddressList[PlayerAddress]['ID'], "Connected": 0}, "Players": self.LobbyDataToSend}).encode("ascii")), PlayerAddress)
        except:
            pass
        if PlayerAddress in self.AddressList:
            print("ID ", self.AddressList[PlayerAddress]['ID']," disconnected.")
            self.RemovePlayerFromLocal(PlayerAddress)

    def RemovePlayerFromLocal(self, PlayerAddress):
        self.idList.remove(self.AddressList[PlayerAddress]['ID'])
        if self.AddressList[PlayerAddress]['Local']['Name'] == "Room":
            del(self.RoomsList[self.AddressList[PlayerAddress]['Local']['Data']["ID"]]["Players"][self.AddressList[PlayerAddress]['ID']])
            self.OnPlayerLeftRoom(self.AddressList[PlayerAddress]['Local']['Data']["ID"])
        elif self.AddressList[PlayerAddress]['Local']['Name'] == "Lobby":
            del(self.LobbyDataToSend[self.AddressList[PlayerAddress]['ID']])
        del(self.AddressList[PlayerAddress])
    
    def GetDataFromLocal(self):
        DataToSend = None
        if self.AddressList[self.address]['Local']['Name'] == "Lobby":
            self.LobbyDataToSend[self.AddressList[self.address]['ID']] = self.SendDict()
            DataToSend = self.LobbyDataToSend
        elif self.AddressList[self.address]['Local']['Name'] == "Room":
            self.RoomsList[self.AddressList[self.address]['Local']['Data']["ID"]]["Players"][self.AddressList[self.address]['ID']] = self.SendDict()
            DataToSend = self.RoomsList[self.AddressList[self.address]['Local']['Data']["ID"]]["Players"]
        return DataToSend;

    def ExecCommand(self):
        while self.Work:
            command = input('')

            if command == 'q' or command == 'quit':
                self.Work = False

            time.sleep(0.1)

    def CheckTimeOut(self):
        for addr in self.AddressList:
            if time.clock() - self.AddressList[addr]['Timeout'] > self.TimeOut:
                print("ID ", self.AddressList[addr]['ID']," disconnected(Timeout).")
                self.RemovePlayerFromLocal(addr)
                #self.idList.remove(self.AddressList[addr]['ID'])
                #del(self.LobbyDataToSend[self.AddressList[addr]['ID']])
                #del(self.AddressList[addr])
                break

    def Quit(self):
        self.Work = False
        self.inputThread.join()
        self.serverSock.close()
        print("Exited!!!")
    

