def sum_to(arr, sum=10):
    """
    Function to find all the pairs of numbers in an array that sum to the provided var (default 10)
    :param arr: the array to search for number pairs
    :param sum: the sum to find
    :return: an array of number pairs
    """
    result = []
    for i in arr:
        for j in arr:
            if i+j == sum:
                # Found a pair that sum to the reqired var
                # ensure that the pair isn't already in the array in a different order
                pair = sorted([i,j])
                if not pair in result:
                    result.append(pair)
    return result

def create_bin_arr(size=10):
    print "Creating the Array..."
    bin_arr = []
    start = 1000000000000000000
    for bin in range(start,start+size):
        bin_arr.append("{0:b}".format(bin))
    return bin_arr

def count_bits(arr):
    print "Counting the 1 bits..."
    num_on_bits = 0
    for bin in arr:
        num_on_bits += len(bin.replace('0',''))

    return num_on_bits

def display_only_uniq(start, end):
    """
    Only display the numbers where all digits are uniq from the range start to end
    :param start: start of number range
    :param end: end of number range
    :return: array of numbers with all uniq digits
    """
    result = []
    for num in range(start, end):
        num_str = str(num)
        if len(list(num_str)) == len(set(num_str)):
            result.append(num_str)

    return result

if __name__ == '__main__':
    #numbers = [0,1,2,3,4,5,6,7,8,10,11,-1,-2,-3,8.4,1.6,5.4]
    #print sum_to(numbers, 10)
    #print count_bits(create_bin_arr(10000000))
    print len(display_only_uniq(10, 1000000))
