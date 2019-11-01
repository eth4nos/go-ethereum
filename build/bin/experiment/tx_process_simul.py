from web3 import Web3
import sys
import socket
import os
import random
import mongoAPI
import json
import rlp
import time
import binascii
import numpy as np

# Log period
EPOCH = 172800

# Path
DB_PATH = "/data/db_full/"
SYNC_DB_PATH = "../data/sync_172863/"

# Settings
FULL_PORT = "8081"
SYNC_PORT = "8082"
PASSWORD = "1234"

# Block numbers
START_BLOCK_NUM = int(sys.argv[1])
END_BLOCK_NUM = int(sys.argv[2])

# providers
fullnode = Web3(Web3.HTTPProvider("http://localhost:" + FULL_PORT))
syncnode = Web3(Web3.HTTPProvider("http://localhost:" + SYNC_PORT))
enode = fullnode.geth.admin.nodeInfo()['enode']

# amount of tx to send
MAX_TX_COUNT = 100
# # of sended tx
txCount = 0
rstxCount = 0

# functions

def main():
    f = open("./mapper.json", 'r')
    mapper = f.read()
    mapper = json.loads(mapper)
    f.close()

    print("From block#", START_BLOCK_NUM, " to #", END_BLOCK_NUM)

    # unlock coinbase
    fullnode.geth.personal.unlockAccount(fullnode.eth.coinbase, PASSWORD, 0)
    syncnode.geth.personal.unlockAccount(syncnode.eth.coinbase, PASSWORD, 0)

    # get current block
    # startBlock = fullnode.eth.blockNumber
    # currentBlock = fullnode.eth.blockNumber

    # main loop for send txs
    for currentBlock in range(START_BLOCK_NUM-7000001, END_BLOCK_NUM-7000001+1):
        transactions = mongoAPI.findMany('transactions_7ms', ['blockNum'], [currentBlock])
        txNumber = len(transactions)

        # send txs for next block
        #print("CURRENT BLOCK #%07d" % currentBlock, end=', ')
        print("NEXT DB_BLOCK #%07d" % currentBlock, end=', ')
        print("TX #%05d" % txNumber, end=', ')
        print("RESTORE #%05d" % len(mapper[currentBlock]))
        for j in range(txNumber):
            to = transactions[j]['to']
            delegatedFrom = transactions[j]['from']
            sendTransaction(to, delegatedFrom)
            print("Send Tx# {0}".format(j), end="\r")

        # restore transaction
        if len(mapper[currentBlock]) == 0:
            # rstxCheck(currentBlock, 0, 0, 0)
            pass
        else:
            sendRestoreTx(currentBlock, mapper[currentBlock])
            # rstxCheck(currentBlock, rstx_min, rstx_max, rstx_avg)

        # mining
        # fullnode.geth.miner.start(1)  # start mining
        # while (currentBlock <= startBlock+i-START_BLOCK_NUM):
        #     currentBlock = fullnode.eth.blockNumber  # wait for mining
        # fullnode.geth.miner.stop()  # stop mining

        # size check
        # if currentBlock % SIZE_CHECK_PERIOD == 0:
        #     sizeCheck(currentBlock)

        # fast sync
        # pivotBlockMod = abs(currentBlock-64) % EPOCH
        # if pivotBlockMod == EPOCH-1:
        #     start_sync = time.time()
        #     synced = fastSync(currentBlock)
        #     while not synced:
        #         # try to keep fast sync while 1 hour
        #         if time.time() - start_sync >= 3600:
        #             break
        #         synced = fastSync(currentBlock)


def sendTransaction(to, delegatedFrom):
    global txCount
    global rstxCount

    isRstx = (to == "0x0123456789012345678901234567890123456789")

    checkCanFinish()
    if (not isRstx) and (txCount >= MAX_TX_COUNT):
        return
    if (isRstx) and (rstxCount >= MAX_TX_COUNT):
        return

    while True:
        try:
            syncnode.eth.sendTransaction(
                {'to': to, 'from': syncnode.eth.coinbase, 'value': '0', 'data': delegatedFrom, 'gas': '0'})
            break
        except:
            continue
    
    if isRstx:
        rstxCount += 1
    else:
        txCount += 1


def checkCanFinish():
    global txCount
    global rstxCount

    if (txCount == MAX_TX_COUNT) and (rstxCount == MAX_TX_COUNT):
        print("Completly Send 200 Txs")
        sys.exit()
    

# def rstxCheck(n, s1, s2, s3):
#     Cmd = "printf \"" + str(n) + " \" >> " + RSTX_PATH
#     os.system(Cmd)
#     Cmd = "printf \"" + str(s1) + " \" >> " + RSTX_PATH
#     os.system(Cmd)
#     Cmd = "printf \"" + str(s2) + " \" >> " + RSTX_PATH
#     os.system(Cmd)
#     Cmd = "printf \"" + str(s3) + "\n\" >> " + RSTX_PATH
#     os.system(Cmd)


# def sizeCheck(n):
#     # (LOG: block# db_size)
#     Cmd = "printf \"" + str(n) + " \" >> " + DB_LOG_PATH
#     os.system(Cmd)
#     Cmd = "du -sc " + DB_PATH + "geth/chaindata | cut -f1 | head -n 1 >> " + DB_LOG_PATH
#     os.system(Cmd)


# def fastSync(n):
#     print("FAST SYNC START!")
#     try:
#         # connecting to the fast sync server
#         s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         s.connect(("localhost", int(READY_PORT)))
#         # check syncnode provider connection
#         connected = syncnode.isConnected()
#         while not connected:
#             connected = syncnode.isConnected()
#         # start sync
#         syncnode.geth.admin.addPeer(enode)
#         # wait until start sync
#         syncdone = syncnode.eth.syncing
#         while syncdone is False:
#             syncdone = syncnode.eth.syncing
#         # wait until state sync done
#         while syncdone.knownStates != syncdone.pulledStates or syncdone.knownStates == 0 or syncdone.currentBlock < syncdone.highestBlock - 64:
#             syncdone = syncnode.eth.syncing
#         print("[FAST SYNC] STATE SYNC DONE!")
#         # after state sync done (LOG: block# pulled-states state_db_size total_db_size)
#         Cmd = "printf \"" + str(n) + " \" >> " + SYNC_LOG_PATH
#         os.system(Cmd)
#         Cmd = "printf \"" + str(syncdone.pulledStates) + \
#             " \" >> " + SYNC_LOG_PATH
#         os.system(Cmd)
#         Cmd = "du -sc " + SYNC_DB_PATH + \
#             "geth/chaindata | cut -f1 | head -n 1 | tr -d '\n' >> " + SYNC_LOG_PATH
#         os.system(Cmd)
#         Cmd = "printf \" \" >> " + SYNC_LOG_PATH
#         os.system(Cmd)
#         # wait until whole fast sync done and terminate
#         while connected:
#             connected = syncnode.isConnected()
#         # after whole fast sync done (LOG: total_db_size)
#         Cmd = "du -sc " + SYNC_DB_PATH + \
#             "geth/chaindata | cut -f1 | head -n 1 >> " + SYNC_LOG_PATH
#         os.system(Cmd)
#         print("[FAST SYNC] BLOCK SYNC DONE!")
#         return True
#     except:
#         return False


def sendRestoreTx(currentBlock, addresses):
    global rstxCount

    checkCanFinish()
    if rstxCount >= MAX_TX_COUNT:
        return
    

    latestCheckPoint = currentBlock - (currentBlock % EPOCH) - 1
    latestCheckPoint = 0 if latestCheckPoint < 0 else latestCheckPoint

    rlpeds = list()
    for r, address in enumerate(addresses):
        proofs = list()
        targetBlocks = list(range(latestCheckPoint - EPOCH, 0, -EPOCH))
        for targetBlock in targetBlocks:
            proof = fullnode.eth.getProof(
                Web3.toChecksumAddress(address),
                [],
                block_identifier=targetBlock
            )
            proofs.append(proof)
            if proof['restored']:
                break

        #print(currentBlock, proofs, targetBlocks)

        proofs.reverse()
        targetBlocks.reverse()

        """
        Compact Form Proof
        """
        tmps = proofs[:]  # deep copy
        for tmp in tmps:
            if tmp['IsVoid']:
                proofs.pop(0)
                targetBlocks.pop(0)
            else:
                break

        tmps = proofs[:]
        for i, tmp in enumerate(tmps):
            try:
                if (tmps[i + 1])['IsVoid']:
                    break
                else:
                    proofs.pop(0)
                    targetBlocks.pop(0)
            except:
                pass

        preRlp = list()
        preRlp.append(address)
        preRlp.append(0 if len(targetBlocks) == 0 else targetBlocks[0])
        if len(targetBlocks) == 0:
            return  # no proofs, do not send rstx

        for proof in proofs:
            preRlp.append(1 if proof['isBloom'] else 0)
            if not proof['isBloom']:
                pfs = proof['accountProof']
                preRlp.append(len(pfs))
                for pf in pfs:
                    preRlp.append(pf)

        # print("> preRlp: ", preRlp)

        rlped = rlp.encode(preRlp)
        # print("> rlped : ", rlped)
        rlpeds.append(len(binascii.hexlify(rlped)))

        sendTransaction("0x0123456789012345678901234567890123456789", rlped)
        print("Restore Tx# {0}".format(r), end="\r")

    # return min(rlpeds), max(rlpeds), np.average(rlpeds)


if __name__ == "__main__":
    main()
    print("DONE")