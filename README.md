# NFT-ERC1155

create a .env file as same in the same format as .env-sample file.

add PRIVATE_KEY, API_URL, WALLET_ADDRESS in the .env

## To get pinata api_key and secret_key,
1. open 'https://app.pinata.cloud'
2. sign in/sign up into pinata
3. Click on Developer option
4. Click on 'New Key' and create a new key
5. copy api_key and secret_key

install pinataPy by running `pip install pinatapy-vourhey`

import in our file as 
```
from pinatapy import PinataPy
pinata_api_key = api_key_of_pinata
pinata_secret_api_key = secret_key_of_pinata
pinata = PinataPy(<pinata_api_key>, <pinata_secret_api_key>)
```

## Steps to be followed to Mint ERC1155 NFT:
1. Convert digital asset into IPFS hash
2. Create a .json file and put the IPFS hash in it
3. Convert the .json file as IPFS Hash and get the IPFS
4. Deploy contract and get the Contract address
5. Mint NFT using the Contract address
6. Add the NFT to listing
7. purchase NFT
8. withdraw the MATIC from contract

## Commands to be followed to achieve the above:

To Convert Digital asset into IPFS - `python3 NFTTrade.py -ip -path filepath`

To Create .json - `python3 NFTTrade.py -md -tt 'trait_type' -val 'value' -ds 'description' -jd 'IPFS hash we got in the step 1' -nm 'name of nft'`

To convert the .json into metadata - `python3 NFTTrade.py -ip -path .json_filepath`
					
To deploy the contract address - `python3 NFTTrade.py -d -n name -s symbol`

To Mint NFT - `python3 NFTTrade.py -m -e edition -mh metadata -a contractAddress`

To Add NFT to list - `python3 NFTTrade.py -al -a contractAddress -pr price of nft -tid token id`
 
To Purchase NFT - `python3 NFTTrade.py -pur -a contractAddress -e edition -tid token id -amt exact price`

To withdraw - `python3 NFTTrade.py -wd -amt amount to be withdrawn from contract's balance`



