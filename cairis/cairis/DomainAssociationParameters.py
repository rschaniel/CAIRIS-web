#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing,
#  software distributed under the License is distributed on an
#  "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
#  KIND, either express or implied.  See the License for the
#  specific language governing permissions and limitations
#  under the License.


import ObjectCreationParameters

class DomainAssociationParameters(ObjectCreationParameters.ObjectCreationParameters):
  def __init__(self,headName,tailName,desc='',cDom=''):
    ObjectCreationParameters.ObjectCreationParameters.__init__(self)
    self.theHeadDomain = headName
    self.theTailDomain = tailName
    self.thePhenomena = desc
    self.theConnectionDomain = cDom

  def headDomain(self): return self.theHeadDomain
  def tailDomain(self): return self.theTailDomain
  def phenomena(self): return self.thePhenomena
  def connectionDomain(self): return self.theConnectionDomain
