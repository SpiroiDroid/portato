# -*- coding: utf-8 -*-
#
# File: portato/mq.pyx
# This file is part of the Portato-Project, a graphical portage-frontend.
#
# Copyright (C) 2006-2009 René 'Necoro' Neumann
# This is free software.  You may redistribute copies of it under the terms of
# the GNU General Public License version 2.
# There is NO WARRANTY, to the extent permitted by law.
#
# Written by René 'Necoro' Neumann <necoro@necoro.net>

class MessageQueueError(Exception):
    pass

class MessageQueueRemovedError (MessageQueueError):
    pass

cdef class MessageQueue (object):

    CREAT = IPC_CREAT
    EXCL = IPC_EXCL
    
    cdef int msgid
    cdef readonly key_t key

    def __init__ (self, key = None, int flags = 0):

        if (flags & IPC_EXCL) and not (flags & IPC_CREAT):
            raise MessageQueueError("EXCL must be combined with CREAT.")

        if key is None and not (flags & IPC_EXCL):
            raise MessageQueueError("The key can only be None if EXCL is set.")

        # make sure there is nothing ... obscure
        flags &= (IPC_CREAT | IPC_EXCL)

        flags |= 0600 # mode

        if key is None:
            check = True
            while check:
                self.key = self.random_key()
                self.msgid = msgget(self.key, flags)
                check = (self.msgid == -1 and errno == EEXIST)
        else:
            self.key = key
            self.msgid = msgget(key, flags)

        if self.msgid == -1:
            if errno == EACCES:
                raise MessageQueueError("Permission denied.")
            elif errno == EEXIST:
                raise MessageQueueError("Queue already exists.")
            elif errno == ENOENT:
                raise MessageQueueError("Queue does not exist and CREAT is not set.")
            elif errno == ENOMEM or errno == ENOSPC:
                raise MessageQueueError("Insufficient ressources.")
            else:
                raise OSError(errno, strerror(errno))

    def remove (self):
        cdef msqid_ds info
        cdef int ret

        ret = msgctl(self.msgid, IPC_RMID, &info)

        if ret == -1:
            if errno == EIDRM or errno == EINVAL:
                raise MessageQueueRemovedError("Queue already removed.")
            elif errno == EPERM:
                raise MessageQueueError("Permission denied.")
            else:
                raise OSError(errno, strerror(errno))

    def send (self, message, int type = 1):
        cdef msg_data * msg
        cdef int ret
        cdef long size = len(message)

        if type <= 0:
            raise ValueError("type must be > 0")

        if size >= MAX_MESSAGE_SIZE:
            raise ValueError("Message must be smaller than %d", MAX_MESSAGE_SIZE)

        msg = <msg_data*>PyMem_Malloc(sizeof(msg_data) + size)

        if msg is NULL:
            raise MemoryError("Out of memory")

        memcpy(msg.mtext, <char*>message, size)
        msg.mtype = type

        with nogil:
            ret = msgsnd(self.msgid, msg, size, 0)

        try:
            if ret == -1:
                if errno == EIDRM or errno == EINVAL:
                    raise MessageQueueRemovedError("Queue was removed.")
                elif errno == EINTR:
                    raise MessageQueueError("Signaled while waiting.")
                elif errno == EACCES:
                    raise MessageQueueError("Permission denied.")
                else:
                    raise OSError(errno, strerror(errno))
        finally:
            PyMem_Free(msg)

    def receive (self):
        cdef msg_data * msg
        cdef int ret
        cdef object retTuple

        msg = <msg_data*>PyMem_Malloc(sizeof(msg_data) + MAX_MESSAGE_SIZE)

        if msg is NULL:
            raise MemoryError("Out of memory")

        msg.mtype = 0

        with nogil:
            ret = msgrcv(self.msgid, msg, <size_t>MAX_MESSAGE_SIZE, 0, 0)
        
        try:
            if ret == -1:
                if errno == EIDRM or errno == EINVAL:
                    raise MessageQueueRemovedError("Queue was removed.")
                elif errno == EINTR:
                    raise MessageQueueError("Signaled while waiting.")
                elif errno == EACCES:
                    raise MessageQueueError("Permission denied.")
                else:
                    raise OSError(errno, strerror(errno))

            retTuple = (PyString_FromStringAndSize(msg.mtext, ret), msg.mtype)
        finally:
            PyMem_Free(msg)

        return retTuple

    cdef key_t random_key (self):
        return <int>(<double>rand() / (<double>RAND_MAX + 1) * INT_MAX)
