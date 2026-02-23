import multiprocessing

if hasattr(multiprocessing, 'freeze_support'):
    multiprocessing.freeze_support()
