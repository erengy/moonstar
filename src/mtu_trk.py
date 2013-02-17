# mtu_trk.py
#
# Extracts data from MTU.TRK, which includes English-Turkish dictionary and
# İngilizce Leb Demeden feature.
#
# MTU.TRK consists of four parts:
#     1- Empty header (3 bytes)
#     2- Offset map for 2-letter prefixes (2028 bytes)
#     3- List of English words (127519 bytes)
#     4- List of Turkish words (702248 bytes)
# All text is encoded in CP 857.

import codecs
import struct

# In MTU.TRK, possibly to reduce the file size and/or obfuscate the data, some
# commonly used suffixes are replaced with bytecode instructions and stored in
# MTU.EXE (1B8B8h-1BC45h) instead. These suffixes are then attached back by
# executing the instructions at runtime.
suffixes = [
    # 7-letter
    "ability", "ibility", "iveness", "ization", "fulness",
    "ousness",
    # 6-letter
    "ectomy", "edness", "liness", "ically", "lessly",
    # 5-letter
    "ality", "alism", "antly", "arian", "ating",
    "ation", "ative", "atory", "berry", "board",
    "bound", "ering", "esque", "fully", "house",
    "ially", "iness", "ingly", "ional", "istic",
    "ition", "ively", "ivity", "light", "ology",
    "orium", "ously", "stone", "ually",
    # 4-letter
    "able", "ance", "ancy", "ally", "ated",
    "back", "ball", "band", "bing", "bird",
    "boat", "bone", "book", "cide", "cule",
    "ding", "down", "ence", "ency", "ener",
    "ette", "fold", "ging", "head", "hood",
    "ible", "ical", "icle", "ings", "ious",
    "itis", "izer", "land", "less", "like",
    "line", "ling", "logy", "make", "ment",
    "ming", "ness", "ning", "ntly", "osis",
    "over", "ping", "ring", "room", "ship",
    "side", "sing", "sman", "some", "ster",
    "tail", "time", "ting", "wise", "wood",
    "work", "wort",
    # 3-letter
    "acy", "ade", "age", "and", "ant",
    "ary", "ate", "ble", "boy", "dom",
    "end", "ent", "ery", "ese", "ess",
    "est", "eur", "ful", "ger", "ial",
    "ian", "ide", "ied", "ier", "ile",
    "ily", "ine", "ing", "ion", "ise",
    "ish", "ism", "ist", "ite", "ity",
    "ium", "ive", "ize", "kin", "ler",
    "let", "man", "med", "nce", "ned",
    "oid", "ome", "oon", "ory", "ous",
    "out", "per", "red", "rer", "sed",
    "ted", "ter", "tic", "ual", "ule",
    "ure", "way", "yer",
    # 2-letter
    "ae", "al", "an", "ar", "by",
    "ch", "cy", "ed", "el", "en",
    "er", "et", "ey", "fy", "ia",
    "ic", "ie", "in", "is", "ly",
    "nt", "on", "or", "ow", "ry",
    "st", "th", "to", "ty", "us",
]

def ExpandMorpheme(prefix_index, morpheme, previous_morpheme, instruction, suffix_index):
    # Calculate first two letters using prefix index. We have 26 * 26 = 676
    # prefixes in total (aa-zz), although only 253 of them are actually used in
    # dictionary entries.
    prefix = chr(ord('a') + prefix_index // 26) + chr(ord('a') + prefix_index % 26)

    if instruction is 0x00 or instruction is 0x12:
        # Nothing to do here
        pass
    elif instruction is 0x20:
        # Capitalize word
        prefix = prefix.title()
    elif 0x40 < instruction < 0x50:
        # Combine the first n characters of the previous morpheme with this one
        n = instruction - 0x40
        morpheme = previous_morpheme[:n] + morpheme
    elif 0x60 < instruction < 0x70:
        # Same as above, capitalized
        n = instruction - 0x60
        morpheme = previous_morpheme[:n] + morpheme
        prefix = prefix.title()
    elif instruction is 0x80:
        # Attach a suffix to the morpheme
        morpheme = morpheme + suffixes[suffix_index]
    elif instruction is 0xA0:
        # Same as above, capitalized
        morpheme = morpheme + suffixes[suffix_index]
        prefix = prefix.title()
    elif 0xC0 < instruction < 0xD0:
        # Combine the first n characters of the previous morpheme with this one,
        # then attach a suffix to it
        n = instruction - 0xC0
        morpheme = previous_morpheme[:n] + morpheme + suffixes[suffix_index]
    elif 0xE0 < instruction < 0xF0:
        # Same as above, capitalized
        n = instruction - 0xE0
        morpheme = previous_morpheme[:n] + morpheme + suffixes[suffix_index]
        prefix = prefix.title()

    return prefix + morpheme

def ReadFile():
    data = open("data\\MTU.TRK", "rb").read()

    # Skip first 3 bytes. Not sure why these bytes exist, but it's all empty 
    # anyway.
    pos = 3

    # Read offset map, where each offset corresponds to a 2-letter prefix 
    # (aa-zz) and consists of 3 bytes.
    offsets = [0] * (26 * 26)
    for i in range(0, len(offsets)):
        bytes = data[pos:pos + 3] + b'\x00' # struct.unpack() requires 4 bytes
        offsets[i] = struct.unpack("<L", bytes)[0]
        pos += 3
    base_offset = pos

    # Read English and Turkish words
    dictionary = []
    previous_word = ''
    for i in range(0, len(offsets)):
        # Read all entries within the offset range
        while pos < base_offset + offsets[i]:
            # Instructions are used to form words from morphemes
            instruction = data[pos]
            pos += 1
            suffix_index = 0
            if instruction >= 0x80:
                # Instructions above 0x80 are followed by a suffix parameter
                suffix_index = data[pos]
                pos += 1

            # English entries are terminated by a 0xFF character
            en_len = 0
            while data[pos + en_len] is not 0xFF:
                en_len += 1
            english = data[pos:pos + en_len].decode("cp857")
            english = ExpandMorpheme(i, english, previous_word, instruction, suffix_index)
            previous_word = english[2:] # No need to store the prefix
            pos += en_len + 1

            # Some Turkish entries are empty
            turkish = ''
            # Offsets of Turkish entries are middle-endian, so it's easier to
            # calculate this ourselves than relying on struct.unpack()
            tr_offset = data[pos + 1] | (data[pos + 2] << 8) | (data[pos] << 16)
            pos += 3
            # 14 entries are corrupted, even the original application displays
            # them as garbage, so we'll just ignore them: aeze, auction,
            # believe in, beneficial, blackmail, correlation, encore, Hebrew,
            # hurricane, jut, march, orient, performance, rubbishy
            if tr_offset > 0:
                tr_pos = base_offset + tr_offset
                tr_len = struct.unpack("<H", data[tr_pos: tr_pos + 2])[0]
                tr_pos += 2
                if tr_len > 0:
                    turkish = data[tr_pos:tr_pos + tr_len]
                    turkish = turkish.decode("cp857")
                    # Replacing backticks with apostrophes
                    turkish = turkish.replace('\x60', '\'')
                    # Different meanings are separated by a 0xFF in CP 857
                    # (0xA0 in Unicode), which we replace with a '#'
                    turkish = turkish.replace('\xA0', '#')

            # Add a new entry to our dictionary
            dictionary.append((english, turkish))

    # Export in plain text. This results in 17988 entries in total, including 14
    # invalid ones.
    with codecs.open("output\\MTU.TRK.TXT", "w", "utf-8") as file:
        for english, turkish in dictionary:
            file.write(english)
            file.write(' ' * (30 - len(english))) # padding
            file.write(turkish)
            file.write('\n')

if __name__ == "__main__":
    ReadFile()