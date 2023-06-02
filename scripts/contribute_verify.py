#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022-2023 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains tools for verifying the service behaviour."""

import json
import os
from pathlib import Path
from typing import Dict

import requests
from web3 import Web3


CONFIG = {
    "prod": {
        "dynamic_contribution_contract_address": "0x02c26437b292d86c5f4f21bbcce0771948274f84",
        "earliest_block_to_monitor": 16097553,
        "latest_block_to_monitor": "latest",
        "infura_url": f"https://mainnet.infura.io/v3/{os.environ.get('INFURA_API_KEY')}",
        "abi_file_path": Path(
            "packages",
            "valory",
            "contracts",
            "dynamic_contribution",
            "build",
            "DynamicContribution.json",
        ),
        "leaderboard_sheet_id": "1y-N033k42sacqOkeHT53QPCd-pFtQEfeXiOCgEUDddw",
        "leaderboard_points_range": "Ranking!B2:C302",
        "leaderboard_layers_range": "Layers!B1:Z3",
        "leaderboard_api_key": os.environ.get("LEADERBOARD_API_KEY"),
        "service_endpoint": "https://pfp.autonolas.tech",
    },
    "staging": {
        "dynamic_contribution_contract_address": "0x7c3b976434fae9986050b26089649d9f63314bd8",
        "earliest_block_to_monitor": 8053690,
        "latest_block_to_monitor": "latest",
        "infura_url": f"https://goerli.infura.io/v3/{os.environ.get('INFURA_API_KEY')}",
        "abi_file_path": Path(
            "packages",
            "valory",
            "contracts",
            "dynamic_contribution",
            "build",
            "DynamicContribution.json",
        ),
        "leaderboard_sheet_id": "12p7sUM5-bgWfg2M_dWXQ21Br98AyTEJ3QJ1cVzapVKs",
        "leaderboard_points_range": "Ranking!B2:C302",
        "leaderboard_layers_range": "Layers!B1:Z3",
        "leaderboard_api_key": os.environ.get("LEADERBOARD_API_KEY"),
        "service_endpoint": "https://pfp.staging.autonolas.tech",
    },
}

POINT_TO_HASHES = {
    "0": "bafybeiabtdl53v2a3irrgrg7eujzffjallpymli763wvhv6gceurfmcemm",
    "100": "bafybeid46w6yzbehir7ackcnsyuasdkun5aq7jnckt4sknvmiewpph776q",
    "50000": "bafybeigbxlwzljbxnlwteupmt6c6k7k2m4bbhunvxxa53dc7niuedilnr4",
    "100000": "bafybeiawxpq4mqckbau3mjwzd3ic2o7ywlhp6zqo7jnaft26zeqm3xsjjy",
    "150000": "bafybeie6k53dupf7rf6622rzfxu3dmlv36hytqrmzs5yrilxwcrlhrml2m",
}

NULL_ADDRESS = "0x0000000000000000000000000000000000000000"

NORMAL = "\033[0m"
RED = "\033[31m"


def get_token_to_address(config: Dict) -> Dict:
    """Read minted tokens and get their ids and minter addresses"""

    web3 = Web3(Web3.HTTPProvider(config["infura_url"]))

    with open(config["abi_file_path"], "r", encoding="utf-8") as abi_file:
        abi = json.load(abi_file)["abi"]

    factory_contract = web3.eth.contract(
        address=Web3.toChecksumAddress(config["dynamic_contribution_contract_address"]),
        abi=abi,
    )

    # Avoid parsing too many blocks at a time. This might take too long and
    # the connection could time out.
    MAX_BLOCKS = 300000
    from_block = config["earliest_block_to_monitor"]
    to_block = (
        web3.eth.get_block_number()
        if config["latest_block_to_monitor"] == "latest"
        else config["latest_block_to_monitor"]
    )
    ranges = list(range(from_block, to_block, MAX_BLOCKS)) + [to_block]

    entries = []

    for i in range(len(ranges) - 1):
        from_block = ranges[i]
        to_block = ranges[i + 1]
        entries += factory_contract.events.Transfer.createFilter(
            fromBlock=from_block,  # exclusive
            toBlock=to_block,  # inclusive
            argument_filters={"from": NULL_ADDRESS},
        ).get_all_entries()  # limited to 10k entries for now: https://github.com/valory-xyz/contribution-service/issues/13

    token_id_to_member = {
        str(entry["args"]["id"]): entry["args"]["to"] for entry in entries
    }

    return token_id_to_member


def get_address_to_points(config: Dict) -> Dict:
    """Read leaderboard"""

    leaderboard_base_endpoint = "https://sheets.googleapis.com/v4/spreadsheets"

    leaderboard_endpoint = f"{leaderboard_base_endpoint}/{config['leaderboard_sheet_id']}/values:batchGet?ranges={config['leaderboard_layers_range']}&ranges={config['leaderboard_points_range']}&key={config['leaderboard_api_key']}"

    response = requests.get(leaderboard_endpoint)

    for data in response.json()["valueRanges"]:
        if data["range"] == config["leaderboard_points_range"]:
            return dict(data["values"])

    raise ValueError("Could not retrieve the leaderboard")


def get_token_image_hash(token_id: str, config: Dict) -> str:
    """Get the token's image hash"""
    url = f"{config['service_endpoint']}/{token_id}"
    response = requests.get(url)
    return response.json()["image"].split("/")[-1]


def get_image(points: str) -> str:
    """Get the image hash given the points"""
    thresholds = list(sorted(POINT_TO_HASHES.keys(), reverse=True))
    for t in thresholds:
        if int(points) >= int(t):
            return POINT_TO_HASHES[t]
    raise ValueError(f"Could not get the image hash for {points} points")


def draw_table(  # pylint: disable=too-many-locals,too-many-statements
    deployment: str,
) -> None:
    """Prints the verification table"""

    config = CONFIG[deployment]
    print(f"Drawing {RED}{deployment.upper()}{NORMAL} table...")

    token_to_address_file = "token_to_address.json"  # nosec
    address_to_points_file = "address_to_points.json"  # nosec
    token_to_hash_file = "token_to_hash.json"  # nosec

    # Get minted tokens
    if not os.path.isfile(token_to_address_file):
        print(f"Writing {token_to_address_file}")
        token_to_address = get_token_to_address(config)
        with open(token_to_address_file, "w", encoding="utf-8") as outfile:
            json.dump(token_to_address, outfile, indent=4)
    else:
        print(f"Loading {token_to_address_file}")
        with open(token_to_address_file, "r", encoding="utf-8") as infile:
            token_to_address = json.load(infile)

    # Read leaderboard
    if not os.path.isfile(address_to_points_file):
        print(f"Writing {address_to_points_file}")
        address_to_points = get_address_to_points(config)
        with open(address_to_points_file, "w", encoding="utf-8") as outfile:
            json.dump(address_to_points, outfile, indent=4)
    else:
        print(f"Loading {address_to_points_file}")
        with open(address_to_points_file, "r", encoding="utf-8") as infile:
            address_to_points = json.load(infile)

    # Get expected image hash
    if not os.path.isfile(token_to_hash_file):
        print(f"Writing {token_to_hash_file}")
        token_to_hash = {
            token_id: get_token_image_hash(token_id, config)
            for token_id in token_to_address.keys()
        }
        with open(token_to_hash_file, "w", encoding="utf-8") as outfile:
            json.dump(token_to_hash, outfile, indent=4)
    else:
        print(f"Loading {token_to_hash_file}")
        with open(token_to_hash_file, "r", encoding="utf-8") as infile:
            token_to_hash = json.load(infile)

    # Build table
    table = []
    for token_id, address in token_to_address.items():
        token_data = {
            "token_id": token_id,
            "address": address,
            "points": address_to_points[address]
            if address in address_to_points
            else "N/A",
        }

        token_data["expected_image"] = (
            get_image(token_data["points"])
            if address in address_to_points
            else POINT_TO_HASHES["0"]
        )
        token_data["image"] = token_to_hash[token_id]
        token_data["ok"] = token_data["expected_image"] == token_data["image"]

        table.append(token_data)

    # Account for multiple tokens per address
    # Only the first token gets the improved image
    visited_addresses = []
    for row in table:
        address = row["address"]
        if address in visited_addresses:
            row["expected_image"] = POINT_TO_HASHES["0"]
            row["ok"] = row["expected_image"] == row["image"]
        visited_addresses.append(address)

    # Print table
    print(
        "\nID                    ADDRESS                        POINTS   EXP_IMAGE     IMAGE     OK"
    )
    print("-" * 90)
    for row in table:
        color = NORMAL if row["ok"] else RED
        print(
            f"{color}{row['token_id']:>3}    {row['address']:>40}    {row['points']:>6}    {row['expected_image'][-8:]:>8}    {row['image'][-8:]:>8}   {row['ok']}{NORMAL}"
        )

    print("-" * 90)
    for address, points in address_to_points.items():
        if address not in token_to_address.values():
            print(
                f"{'N/A':>3}    {address:>40}    {points:>6}    {'N/A':>8}    {'N/A':>8}   N/A"
            )


draw_table("prod")
