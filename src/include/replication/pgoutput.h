/*-------------------------------------------------------------------------
 *
 * pgoutput.h
 *		Logical Replication output plugin
 *
 * Copyright (c) 2015, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *		pgoutput.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef PGOUTPUT_H
#define PGOUTPUT_H

#include "utils/palloc.h"

typedef struct PGOutputData {
    MemoryContext context; /* private memory context for transient
                            * allocations */

    /* client info */
    uint32 protocol_version;

    List *publication_names;
    List *publications;
    bool binary;
} PGOutputData;

#endif /* PGOUTPUT_H */
