#! /usr/bin/python3

# mtu_tur.py
#
# Extracts data from MTU.TUR, which is required for Turkish-English dictionary,
# Türkçe Eş Anlamlılar dictionary and Türkçe Leb Demeden feature.
#
# MTU.TRK consists of seven parts:
#     1- Header (12 bytes)
#     2- 1st section (66 bytes)
#     3- 2nd section (2050 bytes)
#     4- 3rd section (45052 bytes)
#     5- 4th section (107100 bytes)
#     6- 5th section (62800 bytes)
#     7- 6th section (3640 bytes)

import os
import struct

# MTU.TUR encodes all text in its own custom alphabet, where 0x00 is 'a', 0x01
# is 'b' and so on.
alphabet = "abcçdefgğhıijklmnoöpqrsştuüvwxyzâ..........î..............û"

def GetSuffixLength(value):
    # 0x00-0x08: 0, 0x08-0x10: 1, 0x10-0x18: 2, (...), 0xb0-0xb8: 22
    if 0x00 <= value < 0xb8:
        return value // 8
    # 0xb8-0xd0: 3, 0xd0-0xe8: 4, 0xe8-0x100: 5
    elif 0xb8 <= value < 0x100:
        return 3 + ((value - 0xb8) // 0x18)
    else:
        return None

def GetSuffixReodered(suffix, value):
    if value >= 0xb8:
        value = (value - 0xb8) % 0x18
        if 0x00 <= value < 0x08:
            # 'abcd' -> 'dabc'
            suffix = suffix[-1] + suffix[:-1]
        elif 0x08 <= value < 0x10:
            # 'abcd' -> 'bcda'
            suffix = suffix[1:] + suffix[0]
        elif 0x10 <= value < 0x18:
            # 'abcd' -> 'dcba'
            suffix = suffix[::-1]

    return suffix

def GetSuffix(data, instructions, base_offset):
    suffix = ''
    suffix_length = GetSuffixLength(instructions[1])

    if suffix_length == 0:
        # TODO: What's the purpose of [2] and [3] here?
        pass
    # One/Two-letter suffixes are formed directly from our custom alphabet.
    elif 1 <= suffix_length <= 2:
        for i in range(0, suffix_length):
            suffix += alphabet[instructions[2 + i]]
    # For anything else, we need to read the suffix from the 5th section.
    else:
        offset = struct.unpack("<H", instructions[2:4])[0]
        pos = base_offset + offset
        for i in range(0, suffix_length):
            index = data[pos + i]
            suffix += alphabet[index]

    suffix = GetSuffixReodered(suffix, instructions[1])

    return suffix

def ByteToHex(value):
    return format(value, '02x')

def ApplyModifications(data, prefix, suffix):
    '''
    data[0]
    - 0x00: ? (20545/26775 = 76%)
    - 0x01: ? (10) only 01 58 01 00
    - 0x02: ? (10) only 02 40 01 00
    - 0x03: ? () only 03 40 02|03 00
    - 0x05: ?
    - 0x06: ?
    - 0x08: ?
    - 0x09: ?
    - 0x0a: ?
    - 0x0b: ?
    - 0x0f: first letter is capitalized
    - 0x20: includes â, î, û (şapka denetimi için?)
    - 0x2f: ? only 2f 59 02 00
    - 0x40: ?
    - 0x60: ?
    - 0x80: ğ to k
    - 0x81: ?
    - 0x82: ?
    - 0x83: ?
    - 0x85: ?
    - 0x86: ?
    - 0x88: ?
    - 0xa0: ?
    - 0xc0: ?

    data[1]
    - 0x00: ?
    - 0x08: ?
    - 0x10: ?
    - 0x18: ?
    - 0x20: ?
    - 0x30: ?
    - 0x40: ?
    - 0x41: first letter is capitalized
    - 0x42: ?
    - 0x44: ?
    - 0x48: ?
    - 0x49: ?
    - 0x4a: ?
    - 0x4c: ?
    - 0x50: ? nc
    - 0x51: ?
    - 0x52: ?
    - 0x54: ?
    - 0x58: ? nc
    - 0x59: first letter is capitalized
    - 0x5a: ? nc
    - 0x5c: ? nc

    data[2]
    - 0x00: ?
    - 0x01: ?
    - 0x02: ?
    - 0x03: ?
    - 0x04: ?
    - 0x05: ?
    - 0x06: ?
    - 0x07: ?
    - 0x0a: ?
    - 0x12: ?
    - 0x13: ?
    - 0x80: ?
    - 0x81: ?
    - 0x82: ?
    - 0x83: ?
    - 0x85: ?
    - 0x86: ?
    - 0x87: ?
    - 0x88: ?
    - 0x89: ?
    - 0x8a: ?
    - 0x8b: ?
    - 0x91: ?
    - 0x93: ?
    - 0xa1: ?
    - 0xa2: ?
    - 0xa3: ?

    data[3]
    - 0x00: ?
    - 0x01: ?
    - 0x02: ?
    - 0x03: ?
    - 0x10: ?
    - 0x33: ?
    - 0x3f: ?
    - 0xc0: ?
    - 0xc3: ?
    - 0xcc: ?
    - 0xd0: ?
    - 0xf0: ?
    - 0xfc: ?
    '''

    # TEMP
    consonants = {'b': 'p', 'c': 'ç', 'd': 't', 'g': 'k', 'ğ': 'k'}
    if suffix and suffix[-1] in consonants:
        suffix = suffix[:-1] + consonants[suffix[-1]]

    return prefix, suffix

def ReadDictionaryEntries(dictionary, data, base_offset, prefixes, section4, section6):
    item_index = 0
    for prefix, count in prefixes:
        if count == 0:
            continue
        for i in range(item_index, item_index + count):
            suffix = GetSuffix(data, section4[i], base_offset)

            section6_index = section4[i][0] # TODO: related to [1] too?
            prefix, suffix = ApplyModifications(section6[section6_index], prefix, suffix)

            # TEMP
            debug = ''
            debug += ByteToHex(section4[i][1] % 8) + '    '
            #debug += ByteToHex(section6[section6_index][0]) + ' '
            #debug += ByteToHex(section6[section6_index][1]) + ' '
            #debug += ByteToHex(section6[section6_index][2]) + ' '
            #debug += ByteToHex(section6[section6_index][3]) + '    '
            if True or len(suffix) < 2:
                debug += ByteToHex(section4[i][1]) + ' '
                debug += ByteToHex(section4[i][0]) + ' '
                #value = section4[i][1] % 4
                #debug += ByteToHex(value) + ' '
                #debug += ByteToHex(section4[i][2]) + ' '
                #debug += ByteToHex(section4[i][3]) + ' '
                debug += '   '

            #if section4[i][1] <= 0xb8 and section4[i][1] % 8 != 0:
            #if True or section6[section6_index][0] == 0x0f:
            #if True or len(suffix) == 19:
            dictionary.append(debug + prefix + suffix)

        item_index += count

def Import(dictionary, path):
    data = open(path, "rb").read()
    pos = 0

    # Skip magic number ("0x4D 0x47 0x32 0x1A")
    pos += 4

    # Read header
    header = []
    for i in range(0, 4):
        length = struct.unpack("<H", data[pos:pos + 2])[0]
        pos += 2
        header.append(length)

    # A combination of English and Turkish letters. See the first 32 letters
    # of the alphabet definition above.
    letter_count = 32

    # 1st section (?)
    # May be a lookup table for letters. The final value ("0x92 0x0C" = 3218)
    # corresponds to the number of items in the 3rd section.
    section1 = []
    for i in range(0, letter_count + 1):
        value = struct.unpack("<H", data[pos:pos + 2])[0]
        pos += 2
        section1.append(value)

    # 2nd section
    # A lookup table for two-letter prefixes. Values correspond to an offset in
    # the 4th section. If an offset is the same as the next one, it means there
    # are no entries that begin with that prefix. With that in mind, we will
    # store the number of entries for each prefix rather than the offsets.
    section2 = []
    for i in range(0, letter_count**2 + 1):
        value = struct.unpack("<H", data[pos:pos + 2])[0]
        pos += 2
        section2.append(value)
    prefixes = []
    for prefix_index in range(0, len(section2) - 1):
        prefix = alphabet[prefix_index // letter_count]
        prefix += alphabet[prefix_index % letter_count]
        count = section2[prefix_index + 1] - section2[prefix_index]
        prefixes.append((prefix, count))

    # 3rd section (?)
    # Disrupting this section causes entries in Turkish-English and Türkçe Eş
    # Anlamlılar dictionaries to lose their suffixes (e.g. "abayı yakmak" ->
    # "aba yak"). Doesn't seem to affect Leb Demeden.
    section3 = []
    for i in range(0, header[1]): # 3218
        pos += 1
        value = struct.unpack("<H", data[pos:pos + 2])[0]
        pos += 2
        section3.append(value)
        pos += 11

    # 4th section
    # Contains instructions to form the entries in Türkçe Leb Demeden feature.
    # The first byte points to an index at the 6th section.
    # The second byte defines the length of the suffix and how it's formed.
    # The last two bytes are either alphabet letters or an offset to a suffix
    # that can be found in the 5th section.
    section4 = []
    for i in range(0, header[0]): # 26775
        section4.append(data[pos:pos + 4])
        pos += 4

    # 5th section
    # This section contains plain-text suffixes, encoded in a custom alphabet.
    # We're skipping this section for now, but we'll read from it later on.
    base_offset = pos
    pos += header[2] # 62800

    # 6th section
    # Seems to be controlling capitalization and other modifications.
    section6 = []
    for i in range(0, header[3]): # 910
        section6.append(data[pos:pos + 4])
        pos += 4

    # We're now ready to read the entries
    ReadDictionaryEntries(dictionary, data, base_offset, prefixes, section4, section6)

def Export(dictionary, path):
    with open(path, "w", encoding="utf-8") as file:
        for entry in dictionary:
            file.write(entry)
            file.write('\n')

def main():
    dictionary = []
    Import(dictionary, os.path.join("..", "data", "MTU.TUR"))
    Export(dictionary, os.path.join("..", "output", "MTU.TUR.TXT"))
    print("Exported", len(dictionary), "entries.") # 26775

if __name__ == "__main__":
    main()