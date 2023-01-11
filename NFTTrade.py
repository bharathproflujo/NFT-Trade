
# import python modules
import os, sys, glob, time, requests, re, traceback, socket, base64
import subprocess, threading, json, argparse
import solcx
from web3 import Web3, middleware
#from compile import abi, bytecode
from os.path import exists
from pinatapy import PinataPy
from dotenv import load_dotenv
from web3.exceptions import ContractLogicError
from web3.gas_strategies.time_based import *
from web3.middleware import geth_poa_middleware
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES, PKCS1_OAEP
# import traceback

from mainStream import focal

class NFTTrade:

    # main init function
    def __init__(self):
        load_dotenv()
        
        self.userDir  = os.path.expanduser('~')
        self.apiUrl   = os.getenv('API_URL')
        # print_exc
        # source meta mask address
        self.fromAddr = os.getenv('WALLET_ADDRESS')
        # source meta mask private key
        self.pvtKey   = os.getenv('PRIVATE_KEY')
        # source pinata api key
        self.pinata_api_key = os.getenv('PINATA_API_KEY')
        # source pinata api secret
        self.pinata_secret_api_key = os.getenv('PINATA_SECRET_KEY')

    # compile solidity file
    def compileSol( self ):
        # target file path
        source = "contracts/ERC1155.sol"

        # target filename
        file = "ERC1155.sol"

        # compiler specification
        spec = {
                "language": "Solidity",
                "sources": {
                    file: {
                        "urls": [
                            source
                        ]
                    }
                },
                "settings": {
                    "optimizer": {
                       "enabled": True
                    },
                    "outputSelection": {
                        "*": {
                            "*": [
                                "metadata", "evm.bytecode", "abi"
                            ]
                        }
                    }
                }
            };

        # catch output
        compileOut = solcx.compile_standard(spec, allow_paths=".")

        # Export contract data into variable
        abi = compileOut['contracts']['ERC1155.sol']['NFTTrade']['abi']
        bytecode = compileOut['contracts']['ERC1155.sol']['NFTTrade']['evm']['bytecode']['object']

        return abi, bytecode

    def convertIpfs(self,path):
        filepath = exists(path)
        # exit()
        jsonData=''
        if(filepath):
            pinata = PinataPy(self.pinata_api_key,self.pinata_secret_api_key)
            result = pinata.pin_file_to_ipfs(path)
            jsonData = result.get('IpfsHash') + '/' + os.path.basename(path)
        else:
            print('path does not exit')
            exit()
        print("Your IPFS hash is: ",jsonData)

    def convertMetadata(self,traitType,Traitvalue,nftDescription, Nftname, jsonData):
        # exit()
        dict={
            "attributes": [
                {
                    "trait_type": traitType,
                    "value": Traitvalue
                }
            ],
            "description": nftDescription,
            "image": f"ipfs://{jsonData}",
            "name": Nftname
        }               

        with open('metadata.json','w') as fp:
            json.dump(dict, fp)
            print('metadata created successfully')

    # deploy contract address
    def deployAddress( self, name, symbol ):
        print('deploying...')
        abi, bytecode = self.compileSol()

        # Web3 ETH provider
        self.web3 = Web3( provider=Web3.HTTPProvider( self.apiUrl ) )
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        self.web3.middleware_onion.add(middleware.time_based_cache_middleware)
        self.web3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
        self.web3.middleware_onion.add(middleware.simple_cache_middleware)

        focal.logger.info(f'Attempting to deploy from account: { self.fromAddr }')

        focal.logger.info(f'Attempting to deploy from account: { self.pvtKey }')

        # Create contract instance
        NFTTrade = self.web3.eth.contract( abi=abi, bytecode=bytecode )
        focal.logger.debug( f"{name}, {symbol}" )

        # Build constructor transaction
        
        constructTxn = NFTTrade.constructor( name, symbol ).buildTransaction(
            {
                "gasPrice": self.web3.eth.gas_price,
                'from': self.fromAddr,
                'nonce': self.web3.eth.getTransactionCount( self.fromAddr ),
            }
        )

        # Sign transaction with Private Key
        txnCreate = self.web3.eth.account.signTransaction( constructTxn, self.pvtKey )

        # Send transaction and wait for receipt
        txnHash = self.web3.eth.sendRawTransaction( txnCreate.rawTransaction )
        txnReceipt = self.web3.eth.waitForTransactionReceipt( txnHash )

        focal.logger.info(f'Contract deployed at address: { txnReceipt.contractAddress }')

    def mintNFT( self, contractAddr, metaDataHash, editionCount ):
        abi, bytecode = self.compileSol()

        # Web3 ETH provider
        self.web3 = Web3( provider=Web3.HTTPProvider( self.apiUrl ) )

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

        metaPath = metaDataHash
        separator = '/'
        metaData = metaPath.split(separator, 1)[0]
       

        contractArgs = [ self.fromAddr, editionCount,  f"ipfs://{metaData}" ]
        print("Contract Arguments:",contractArgs)
        
        fnName = "mint"

        contract = self.web3.eth.contract( contractAddr, abi=abi )
     
        
        contractData = contract.encodeABI( fnName, args=contractArgs )
       
        gas, gasprice, txnFee, nonce = self.calculateMandates( contract, fnName, contractArgs )
        print('jj')
        tfrData = {
            'chainId' : 80001,
            'to': contract.address,
            'from': self.fromAddr,
            'value': Web3.toHex(0),
            'gasPrice': Web3.toHex(gasprice),
            'nonce': nonce,
            'data': contractData,
            'gas': Web3.toHex(gas),
        }

        focal.logger.info(f"Transaction:\n{tfrData}")
        focal.logger.info(f"Function: {fnName}")
        focal.logger.info(f"Arguments:{contractArgs}")
        focal.logger.info(f"Gas Price:{gasprice}")
        focal.logger.info(f"Gas:{gas}")
        focal.logger.info(f"Fees:{txnFee}")

        try:
            
            signed = self.web3.eth.account.signTransaction( tfrData, self.pvtKey )
            txn = self.web3.eth.sendRawTransaction( signed.rawTransaction )
            
            txnReceipt = self.web3.eth.waitForTransactionReceipt( txn )

            for key in txnReceipt:
                if key not in ['blockNumber','cumulativeGasUsed','from','contractAddress','status']:
                    continue

                val = txnReceipt.get(key)
                print(type(val))
                if( isinstance( val, bytes) ):
                    val = val.hex()
                   
                focal.logger.info(f"{key}: %s ", (val,) )
        except Exception as e:
            
            focal.logger.info(f"{fnName} Error: ", e)


    # to add NFT for Sale
    def addToList(self,  contractAddr, price,token_id):
        abi, bytecode = self.compileSol()
       
         # Web3 ETH provider
        wei_amount = price * 10**18
        
        self.web3 = Web3( provider=Web3.HTTPProvider( self.apiUrl ) )

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        contractArgs = [  contractAddr,wei_amount, token_id]
        
        print("Contract Arguments:",contractArgs)
       
        fnName = "addListing"
        
        contract = self.web3.eth.contract( contractAddr, abi=abi )
     
        contractData = contract.encodeABI( fnName, args=contractArgs )

        gas, gasprice, txnFee, nonce = self.calculateMandates( contract, fnName, contractArgs )

        tfrData = {
            'chainId' : 80001,
            'to': contract.address,
            'from': self.fromAddr,
            'value': Web3.toHex(0),
            'gasPrice': Web3.toHex(gasprice),
            'nonce': nonce,
            'data': contractData,
            'gas': Web3.toHex(gas),
        }

        focal.logger.info(f"Transaction:\n{tfrData}")
        focal.logger.info(f"Function: {fnName}")
        focal.logger.info(f"Arguments:{contractArgs}")
        focal.logger.info(f"Gas Price:{gasprice}")
        focal.logger.info(f"Gas:{gas}")
        focal.logger.info(f"Fees:{txnFee}")

        try:
            signed = self.web3.eth.account.signTransaction( tfrData, self.pvtKey )
            txn = self.web3.eth.sendRawTransaction( signed.rawTransaction )
            txnReceipt = self.web3.eth.waitForTransactionReceipt( txn )

            for key in txnReceipt:
                if key not in ['blockNumber','cumulativeGasUsed','from','contractAddress','status']:
                    continue

                val = txnReceipt.get(key)
                print(type(val))
                if( isinstance( val, bytes) ):
                    val = val.hex()

                focal.logger.info(f"{key}: %s ", (val,) )
        except Exception as e:
            focal.logger.info(f"{fnName} Error: ", e)
        
    def purchase(self, contractAddr, editionCount, token_id, amount):
        abi, bytecode = self.compileSol()
        
         # Web3 ETH provider
        self.web3 = Web3( provider=Web3.HTTPProvider( self.apiUrl ) )

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        wei_amount = amount * 10**18
        
        contractArgs = [ contractAddr,editionCount, token_id, wei_amount]
        print("Contract Arguments",contractArgs)
        
        fnName = "purchase"
        
        contract = self.web3.eth.contract( contractAddr, abi=abi )
     
        contractData = contract.encodeABI( fnName, args=contractArgs )

        gas, gasprice, txnFee, nonce = self.calculateMandates( contract, fnName, contractArgs )

        tfrData = {
            'chainId' : 80001,
            'to': contract.address,
            'from': self.fromAddr,
            'value': Web3.toHex(wei_amount),
            'gasPrice': Web3.toHex(gasprice),
            'nonce': nonce,
            'data': contractData,
            'gas': Web3.toHex(gas),
        }

        focal.logger.info(f"Transaction:\n{tfrData}")
        focal.logger.info(f"Function: {fnName}")
        focal.logger.info(f"Arguments:{contractArgs}")
        focal.logger.info(f"Gas Price:{gasprice}")
        focal.logger.info(f"Gas:{gas}")
        focal.logger.info(f"Fees:{txnFee}")

        try:
            signed = self.web3.eth.account.signTransaction( tfrData, self.pvtKey )
            txn = self.web3.eth.sendRawTransaction( signed.rawTransaction )
            txnReceipt = self.web3.eth.waitForTransactionReceipt( txn )

            for key in txnReceipt:
                if key not in ['blockNumber','cumulativeGasUsed','from','contractAddress','status']:
                    continue

                val = txnReceipt.get(key)
                print(type(val))
                if( isinstance( val, bytes) ):
                    val = val.hex()

                focal.logger.info(f"{key}: %s ", (val,) )
        except Exception as e:
            focal.logger.info(f"{fnName} Error: ", e)


    def withdraw(self, contractAddr, amount):
        abi, bytecode = self.compileSol()
        print('kkk')
         # Web3 ETH provider
        self.web3 = Web3( provider=Web3.HTTPProvider( self.apiUrl ) )

        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        wei_amount = amount * 10**18
        
        contractArgs = [wei_amount]
        print("Contract arguments :", contractArgs)
        
        fnName = "withdraw"

        contract = self.web3.eth.contract( contractAddr, abi=abi )
     
        contractData = contract.encodeABI( fnName, args=contractArgs )

        gas, gasprice, txnFee, nonce = self.calculateMandates( contract, fnName, contractArgs )
        
        tfrData = {
            'chainId' : 80001,
            'to': contract.address,
            'from': self.fromAddr,
            'value': Web3.toHex(0),
            'gasPrice': Web3.toHex(gasprice),
            'nonce': nonce,
            'data': contractData,
            'gas': Web3.toHex(gas),
        }
        
        focal.logger.info(f"Transaction:\n{tfrData}")
        focal.logger.info(f"Function: {fnName}")
        focal.logger.info(f"Arguments:{contractArgs}")
        focal.logger.info(f"Gas Price:{gasprice}")
        focal.logger.info(f"Gas:{gas}")
        focal.logger.info(f"Fees:{txnFee}")

        try:
            signed = self.web3.eth.account.signTransaction( tfrData, self.pvtKey )
            txn = self.web3.eth.sendRawTransaction( signed.rawTransaction )
            txnReceipt = self.web3.eth.waitForTransactionReceipt( txn )

            for key in txnReceipt:
                if key not in ['blockNumber','cumulativeGasUsed','from','contractAddress','status']:
                    continue

                val = txnReceipt.get(key)
                print(type(val))
                if( isinstance( val, bytes) ):
                    val = val.hex()

                focal.logger.info(f"{key}: %s ", (val,) )
        except Exception as e:
            focal.logger.info(f"{fnName} Error: ", e)
        
    def calculateMandates( self, contract, fnName, contractArgs ):

        # calculate gas & transaction fees
        csAddr = Web3.toChecksumAddress( self.fromAddr )

        strategy = construct_time_based_gas_price_strategy( 10 )

        self.web3.eth.setGasPriceStrategy( strategy )

        gas = getattr( contract.functions, fnName )(*contractArgs).estimateGas({'from': csAddr})

        gasprice = self.web3.eth.generateGasPrice()

        txnFee = gas * gasprice

        # calculate fees
        nonce = Web3.toHex( self.web3.eth.getTransactionCount(csAddr) )

        return gas, gasprice, txnFee, nonce
#---------------------------------------
# Setup arguments to execute
#---------------------------------------
def initOptions():
    csuc = focal.colors.get("success")
    cinf = focal.colors.get("info")
    cerr = focal.colors.get("error")
    cend = focal.colors.get("off")

    # Create the parser
    parser = argparse.ArgumentParser(
      prog="ERC1155 Mint NFT",
      allow_abbrev=False,
      description=f'{csuc}Process the choosen operation{cend}',
      epilog=f'{cinf}Am the helper of manage porting Rubix NFTs! (^_^){cend}'
    )

    # Mentaion the program version
    parser.version = '1.0'

    # Add the arguments
    parser.add_argument('-c', '--compile', nargs='?', const=True, type=bool, help='For compile the solidity')
    parser.add_argument('-d', '--deploy', nargs='?', const=True, type=bool, help='For deploy contract address')
    parser.add_argument('-ip', '--ipfs', nargs='?', const=True, type=bool, help='For converting our digital asset into ipfs hash')
    parser.add_argument('-md','--metadata',nargs='?',const=True, type=bool, help='For converting our digital asset into metadata')
    parser.add_argument('-path', '--path', type=str, help='For path of digital asset')
    parser.add_argument('-tt', '--traitType', type=str, help='For name of the deployment group')
    parser.add_argument('-val', '--Traitvalue', type=str, help='For trait type of the metadata')
    parser.add_argument('-ds', '--nftDescription', type=str, help='For description of the metadata')
    parser.add_argument('-jd', '--jsonData', type=str, help='For jsonData of the metadata')
    parser.add_argument('-nm', '--Nftname', type=str, help='For name of metadata')
    
    parser.add_argument('-m', '--mint', nargs='?', const=True, type=bool, help='For Minting the NFT')
    parser.add_argument('-n', '--name', type=str, help='For name of the deployment group')
    parser.add_argument('-s', '--symbol', type=str, help='For symbol of the deployment group')
    parser.add_argument('-a', '--address', type=str, help='For address of the contract')
    parser.add_argument('-e', '--edition', type=int, help='For edition count of the nft')
    parser.add_argument('-mh', '--metahash', type=str, help='For meta hash of the contract')
    parser.add_argument('-u', '--url', type=str, help='For API url of the blockchain')
    
    parser.add_argument('-al', '--addListing', nargs='?', const=True, type=bool, help='For Listing NFT for sale')
    parser.add_argument('-pr', '--price', type=int, help='to set the price of the nft') 
    parser.add_argument('-tid', '--token_id', type=int, help='to set the token id of the NFT')
    
    parser.add_argument('-pur', '--purchase', nargs='?', const=True, type=bool, help='For purchasing NFT for sale')
    # parser.add_argument('-ec', '--editionCount', type=str, help='For edition count of NFT')
    
    parser.add_argument('-wd', '--withdraw', nargs='?', const=True, type=bool, help='For withdrawing NFT for sale')
    parser.add_argument('-amt', '--amount', type=int, help='For edition count of the nft')

    return parser



#---------------------------------------
# Main method
#---------------------------------------
def main():
  try:
    mintNFT = NFTTrade()

    argparser = initOptions()

    argparser = focal.configParser( argparser )

    processes = {
                  "compile" : mintNFT.compileSol,
                  "ipfs" : mintNFT.convertIpfs,
                  "deploy" : mintNFT.deployAddress,
                  "mint" : mintNFT.mintNFT,
                  "metadata" : mintNFT.convertMetadata,
                  "addListing" : mintNFT.addToList,
                  "purchase" : mintNFT.purchase,
                  "withdraw" : mintNFT.withdraw
                }

    args = argparser.parse_args()

    argprcd = focal.argProcess( argparser.parse_args() )

    if argprcd:
      exit()

    # Execute the parse_args() method
    args = vars(args)

    # call triggered process
    for call in processes.keys():
        if args[call]:
            func = processes[call]

            if call == 'mint':
                address = args['address']
                metahash = args['metahash']
                edition = args['edition']
                # apiUrl = args['url']

                func( address, metahash, edition )
            elif call == 'deploy':
                name = args['name']
                symbol = args['symbol']
                apiUrl = args['url']

                func( name, symbol)
            elif call == 'metadata':
                traitType = args['traitType']
                Traitvalue = args['Traitvalue']
                nftDescription = args['nftDescription']
                Nftname = args['Nftname']
                jsonData = args['jsonData']
                
                func(traitType,Traitvalue, nftDescription,Nftname, jsonData)
            elif call == 'ipfs':
                path = args['path']
                # pinata = args['pinata']
                func(path)
                
            elif call == 'addListing':
                address = args['address']
                price = args['price']
                tid = args['token_id']
                
                func(address,price,tid)
                
            elif call == 'purchase':
                address = args['address']
                edition = args['edition']
                tid = args['token_id']
                amount = args['amount']
                
                func(address, edition, tid, amount)
                
            elif call == 'withdraw':
                address = args['address']
                amount = args['amount']

                func(address, amount)

            else:
                func()

  except Exception as err:
    # printing stack trace
    # traceback.print_exc()

    focal.logger.error(f"Error caught while process : {repr(err)}" )

    if focal.showLog:
      print(f'Oops...(>_<)')
  finally:
    if focal.showLog:
      exit(f'Bye...(^_^)')

# --------------------------------------------
# Main method declarations
# --------------------------------------------
if __name__ == '__main__':
  main()