// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "node_modules/@openzeppelin/contracts/token/ERC1155/ERC1155.sol";
import "node_modules/@openzeppelin/contracts/access/Ownable.sol";
import "node_modules/@openzeppelin/contracts/token/ERC1155/extensions/ERC1155Supply.sol";
import "node_modules/@openzeppelin/contracts/utils/Counters.sol";

contract NFTTrade is ERC1155, Ownable, ERC1155Supply {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    uint256 public EditionPrice = 2500000000000000 wei;

    string public name;
    string public symbol;

    constructor(string memory NftName, string memory NftSymbol) ERC1155("") {
        name = NftName;
        symbol = NftSymbol;
    }

    event Token_ID(uint256 tokenid);
    event AddToListing(uint256 price, address seller, uint256 tokenID);
    event Transfer(
        address indexed from,
        address indexed to,
        uint256 EditionCount,
        uint256 tokenId,
        uint256 amount
    );

    function mint(
        address account,
        uint256 edition,
        string memory uri
    ) public payable {
        _tokenIds.increment();

        uint256 newItemId = _tokenIds.current();

        require(edition > 0, "Edition count cannot be 0");

        require(
            msg.sender.balance >= EditionPrice * edition,
            "you don't have enough ether to perform this transaction"
        );

        _mint(account, newItemId, edition, "");

        _setURI(uri);

        emit Token_ID(newItemId);
    }

    function _beforeTokenTransfer(
        address operator,
        address from,
        address to,
        uint256[] memory ids,
        uint256[] memory editions,
        bytes memory data
    ) internal override(ERC1155, ERC1155Supply) {
        super._beforeTokenTransfer(operator, from, to, ids, editions, data);
    }

    mapping(address => mapping(uint256 => Listing)) public listings;
    mapping(address => uint256) public balances;

    struct Listing {
        uint256 price;
        address seller;
        uint256 tokenID;
    }

    function addListing(
        address contractAddress,
        uint256 price,
        uint256 tokenId
    ) public {
        require(price > 0, "Price must be at least 1 wei");

        ERC1155 token = ERC1155(contractAddress);

        setApprovalForAll(contractAddress, true);

        require(
            token.balanceOf(msg.sender, tokenId) > 0,
            "Caller Must own given Token"
        );

        listings[contractAddress][tokenId] = Listing(
            price,
            msg.sender,
            tokenId
        );
        emit AddToListing(price, msg.sender, tokenId);
    }

    function purchase(
        address contractAddress,
        uint256 editionCount,
        uint256 tokenId,
        uint256 amount
    ) public payable {
        Listing memory item = listings[contractAddress][tokenId];

        require(
            editionCount > 0,
            "Edition Count should be equal to or more than 1"
        );

        require(msg.sender != item.seller, "You can't buy your own nft");

        require(
            msg.sender.balance >= item.price * editionCount,
            "insufficient funds"
        );
        require(
            amount == item.price * editionCount,
            "Please send the correct amount"
        );

        balances[msg.sender] += amount;

        ERC1155 token = ERC1155(contractAddress);

        token.safeTransferFrom(
            item.seller,
            msg.sender,
            tokenId,
            editionCount,
            ""
        );

        emit Transfer(
            item.seller,
            msg.sender,
            editionCount,
            tokenId,
            msg.value
        );
    }

    function getBalance() public view returns (uint256) {
        return owner().balance;
    }

    function withdraw(uint256 amount) public returns (bool success) {
        require(msg.sender == owner(), "Only the owner can withdraw");

        require(
            amount <= address(this).balance,
            "You've entered more amount than the actual balance"
        );
        payable(msg.sender).transfer(amount);
        return true;
    }
}
