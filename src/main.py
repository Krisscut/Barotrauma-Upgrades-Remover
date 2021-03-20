#

# Interesting documentation.
#https://docs.python.org/3/library/xml.etree.elementtree.html
#https://docs.python.org/fr/3/library/gzip.html

import logging

import gzip # Used to open the .sub file.
import xml.etree.ElementTree as ET #submarine parsing
import glob # list files of an extension in a directory
import os # get current dir
from os import path # file manipulation
import time # program duration
import shutil # write of file to gzip
import re


CWD_DIR = os.getcwd()
SCRIPT_DIR = path.dirname(os.path.realpath(__file__))

EXECUTABLE_MODE = False if SCRIPT_DIR.endswith("Barotrauma-Upgrades-Remover" + os.sep + "src") else True
WORKING_DIR = path.join(SCRIPT_DIR, "./workingDir") if EXECUTABLE_MODE else path.join(SCRIPT_DIR, "../workingDir") # dev versus
INPUT_DIR = path.join(WORKING_DIR, "input")
OUTPUT_DIR = path.join(WORKING_DIR, "output")

NB_LINKED_SUBMARINES = 0
NB_UPGRADES_FOUND = 0

# Recursive function to find upgrades in all items and the linked submarines.
def removeUpgradeFromItem(node):
    global NB_LINKED_SUBMARINES, NB_UPGRADES_FOUND
    logging.info(f"Starting parsing of sub node {node.attrib['name']}")

    for item in node:
        itemName = item.tag
        itemAttribs = item.attrib

        #logging.info(f'tag is {itemName} with attrib {itemAttribs}')

        upgradesToRemove = []
        for upgrade in item.iter('Upgrade'):
            if itemName == "LinkedSubmarine":
                NB_LINKED_SUBMARINES += 1
                removeUpgradeFromItem(item)
            else:
                NB_UPGRADES_FOUND += 1
                itemId = item.attrib['ID']

                # Search for datas first
                upgradeId = upgrade.attrib['identifier']
                upgradeLevel = upgrade.attrib['level']
                for child in upgrade:
                    componentTargetedNode = child
                    break   # need to check if there is a better way to do this

                for statNodeChild in componentTargetedNode:
                    statNode = statNodeChild
                    break

                componentTargeted = componentTargetedNode.tag
                statModified = statNode.tag
                statInitialValue = statNode.attrib['value']

                if componentTargeted == "This": # Special case for wall, property is in the item inself, not in a subnode
                    componentNode = item
                else:
                    for componentNode in item.iter(componentTargeted):  # To find the component
                        break

                # Replace Current values with the ones prior to the upgrade.
                statUpgradedValue = componentNode.attrib[statModified]
                componentNode.attrib[statModified] = statInitialValue

                logging.debug(f"Found an upgrade with id {upgrade.attrib['identifier']}(level {upgradeLevel}). For component {componentTargeted}[{itemId}], property {statModified} with original value {statInitialValue} (restored) and upgraded value {statUpgradedValue} (dropped)")
                upgradesToRemove.append(upgrade)

        for upgradeItemToRemove in upgradesToRemove:
            # Remove upgrade node now that upgrades have been removed from stats.
            item.remove(upgradeItemToRemove)



def removeUpgradeFromXml(submarineStr, editedLocation):

    # Not sure why this is needed yet, seem there are special characters at the start of the file.
    #submarineStr = "<?xml version='1.0' encoding='utf-8'?>" + submarineStr[3:]
    #submarineStr = submarineStr[3:]
    submarineStr = re.sub(r'^.*?<Submarine', '<Submarine', submarineStr)

    # tree = ET.parse(submarineStr)
    # root = tree.getroot()
    root = ET.fromstring(submarineStr)

    removeUpgradeFromItem(root)

    tree = ET.ElementTree(root)
    tree.write(editedLocation, encoding="UTF-8", xml_declaration=False)

    return submarineStr

def main():
    global NB_LINKED_SUBMARINES, NB_UPGRADES_FOUND

    NB_PROCESSED_SUBMARINES = 0
    os.chdir(INPUT_DIR)
    for submarineInputFile in glob.glob("*.sub"):
        NB_PROCESSED_SUBMARINES += 1
        NB_LINKED_SUBMARINES = 0
        NB_UPGRADES_FOUND = 0

        submarineFilenameWithExt = path.basename(submarineInputFile)
        submarineFilenameWithoutExt = os.path.splitext(submarineFilenameWithExt)[0]

        with gzip.open(submarineInputFile,  mode='rb') as f: #'rb'
            uncompressedData = f.read()

        submarineInfo = uncompressedData.decode('utf-8')
        logging.info(f"Read sub file {submarineInputFile}, start parsing.")

        submarineOutputFolder = path.join(OUTPUT_DIR, submarineFilenameWithoutExt)

        if not path.exists(submarineOutputFolder):
            os.makedirs(submarineOutputFolder)

        submarineXmlFilename = submarineFilenameWithoutExt + ".xml"
        submarineXmlFile = path.join(submarineOutputFolder, submarineXmlFilename)

        submarineXmlFilenameEdit = submarineFilenameWithoutExt + "_noUpgrades.xml"
        submarineXmlFileEdit = path.join(submarineOutputFolder, submarineXmlFilenameEdit)

        submarineInfo = removeUpgradeFromXml(submarineInfo, submarineXmlFileEdit)

        logging.info(f"Writing info to output dir {submarineOutputFolder}.")
        submarineInfoAsBytes = submarineInfo.encode('utf-8')
        with open(submarineXmlFile, "wb") as fileOut:    # Write original XML file (edited exported in removeUpgradeFromXml).
            fileOut.write(submarineInfoAsBytes)

        submarineOutputSubFile = path.join(submarineOutputFolder, submarineFilenameWithExt)
        with open(submarineXmlFileEdit, 'rb') as f_in:
            with gzip.open(submarineOutputSubFile, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        logging.info(f"Processed the sub + {NB_LINKED_SUBMARINES} linked submarines. Found {NB_UPGRADES_FOUND} upgrades.")

    logging.info(f"Processed {NB_PROCESSED_SUBMARINES} submarine(s).")

    if NB_PROCESSED_SUBMARINES == 0:
        logging.warning(f"No submarines were processed. You should put the submarine file (.sub) inside the input folder {INPUT_DIR}")


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s %(name)s %(levelname)s:%(message)s', level=logging.DEBUG)

    logging.debug(f"ScriptDir: {SCRIPT_DIR}")
    logging.debug(f"WorkingDir: {WORKING_DIR}")

    # starting time
    start = time.time()
    logging.info("Start script in {} mode".format("EXECUTABLE" if EXECUTABLE_MODE else "SCRIPT"))

    # execute only if run as a script
    main()

    end = time.time()
    logging.info(f"End script after {end - start} seconds")

    # Prevent auto close of the console at the end ...
    if EXECUTABLE_MODE:
        os.system("pause")