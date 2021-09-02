from __future__ import print_function

import sys, os, json, torch, logging, numpy as np, argparse, re, pickle, random, string
from sys import stdout
from os.path import exists, abspath, dirname, join
from collections import Counter
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm
from copy import deepcopy 
from transformers import *

from ioutils import read_lines 
from ads_parser import AdsParser 
from corenlp_parser import CoreNLPParser  
from utils import canonical_name, canonical_component_name, LogUtil, targettab

label2ind = {
  "Contains": 0,
  "O": 1,
}
ind2label = { v:k for k, v in label2ind.items()}



# =========== Model Utils ==============
def add_marker_tokens(tokenizer, ner_labels):
    """
    This function adds entity markers into the tokenizer's vocabulary, such as <ner_start=Target> and <ner_end=Target>
    """
    new_tokens = []
    for label in ner_labels:
        new_tokens.append('<ner_start=%s>'%(label.lower()))
        new_tokens.append('<ner_end=%s>'%(label.lower()))
    tokenizer.add_tokens(new_tokens)


def to_device(tensor, gpu_id):
    """
      Move a tensor to a specific gpu depending on self.gpu_id 
    """
    if gpu_id >= 0:
      return tensor.cuda(gpu_id)
    else:
      return tensor

def pad_seqs(seqs, tensor_type):
      # each seq should be a list of numbers
      # pad each seq to same length 
      # used to pad 
      batch_size = len(seqs)

      seq_lenths = torch.LongTensor([len(s) for s in seqs])
      max_seq_len = seq_lenths.max()

      seq_tensor = torch.zeros(batch_size, max_seq_len, dtype = tensor_type)

      mask = torch.zeros(batch_size, max_seq_len, dtype = torch.long)

      for i, (seq, seq_len) in enumerate(zip(seqs, seq_lenths)):
        seq_tensor[i,:seq_len] = torch.tensor(seq, dtype = tensor_type)
        mask[i,:seq_len] = torch.LongTensor([1]*int(seq_len))
      return seq_tensor, mask


def collate(batch):
    
    batch_size = len(batch)
    item = {}
    sent_inputids, sent_attention_masks = pad_seqs([ins.input_ids for ins in batch], torch.long)
    item["sent_inputids"] = sent_inputids
    item["sent_attention_masks"] = sent_attention_masks
    item["span_widths"] = torch.LongTensor([ins.span_width - 1  for ins in batch])

    item["bert_starts"] = torch.LongTensor([ins.bert_start_idx for ins in batch])
    item["bert_ends"] = torch.LongTensor([ins.bert_end_idx for ins in batch])

    item["labels"] = torch.LongTensor([label2ind[ins.relation_label] for ins in batch]) if batch[0].relation_label is not None else torch.LongTensor([-1] * batch_size)
    item["instances"] = batch

    return item 

class MyDataset(Dataset):
    def __init__(self,instances):

        super(Dataset, self).__init__()
        # first shuffle
        self.instances = instances
        random.Random(100).shuffle(self.instances)

    def __len__(self):
        return len(self.instances)

    def __getitem__(self, i):
        return self.instances[i]

class Model(torch.nn.Module):
  def __init__(self, model_name, gpu_id = 0): 
    """
    Args:
      model_name: either Container or Containee
      gpu_id: denote the GPU device to use. Negative gpu_id indicates not using any gpu
    """
    super(Model, self).__init__()

    logger = logging.getLogger('py.warnings')

    self.model_type = 'bert-base-uncased'
    self.model_name = model_name
    
    self.gpu_id = gpu_id
    if self.gpu_id < 0: 
      logger.info("GPU is not used due to negative GPU ID %s." % (str(self.gpu_id)))

    self.tokenizer = BertTokenizer.from_pretrained(self.model_type)

    if self.model_name == 'Containee':
      add_marker_tokens(self.tokenizer, ['Component'])
    elif self.model_name == 'Container':
      add_marker_tokens(self.tokenizer, ['Target'])
    else:
      logger.error('Unrecognized model name: %s' % (self.model_name))

    self.bert_encoder = AutoModel.from_pretrained(self.model_type)
    self.bert_encoder.resize_token_embeddings(len(self.tokenizer))
    
    self.encoder_dimension = 768
    self.layernorm = torch.nn.LayerNorm(self.encoder_dimension * 3)
    self.linear = torch.nn.Linear(self.encoder_dimension * 3, 2)


  def forward(self, item):
      
      sent_inputids = to_device(item["sent_inputids"], self.gpu_id)
      sent_attention_masks = to_device(item["sent_attention_masks"],  self.gpu_id)
      starts1 = to_device(item["bert_starts"],  self.gpu_id)
      ends1 = to_device(item["bert_ends"],  self.gpu_id)

      last_hidden_states, cls_embds = self.bert_encoder(sent_inputids, attention_mask = sent_attention_masks)

      batch_size, seq_len, dimension = last_hidden_states.size() # get (batch, 2*dimension), [start_embedding, end_embedding]

      start_indices1 = starts1.view(batch_size, -1).repeat(1, dimension).unsqueeze(1)# (batch, 1, dimension)
      start_embeddings1 = torch.gather(last_hidden_states, 1, start_indices1).view(batch_size, -1) # shape (batch, dimension)

      end_indices1 = ends1.view(batch_size, -1).repeat(1, dimension).unsqueeze(1) # (batch, 1, dimension) 
      end_embeddings1 = torch.gather(last_hidden_states, 1, end_indices1).view(batch_size, -1) # shape (batch, dimension)
      
      logits =  self.linear(self.layernorm(torch.cat((start_embeddings1, end_embeddings1, cls_embds), 1)))


      return logits
  

# ============ Instances =================
def truncate(temp_prespan_ids, temp_posspan_ids, num_cut):
    # This function truncates previous and pos-context iteratively for  num_cut times . NOTE, the ids are assume to come with [CLS] and [SEP], and the truncation would not touch these two tokens
    prespan_ids = temp_prespan_ids[:]
    posspan_ids = temp_posspan_ids[:]

    while num_cut and (len(prespan_ids) > 1 or len(posspan_ids) > 1):

        if len(prespan_ids) > 1:
            prespan_ids.pop(1)
            num_cut -= 1

        if num_cut == 0:
            break
        if len(posspan_ids) > 1:
            posspan_ids.pop(-2)
            num_cut -= 1
        if num_cut == 0:
            break
    return prespan_ids, posspan_ids, num_cut

class Span_Instance:
    def __init__(self, venue, year, docname, doc_start_char, doc_end_char, text, ner_label, sent_toks = None, sentid = None, sent_start_idx = None, sent_end_idx = None):
        """ 
        This class is designed to store information for an entity such as Target, Element and Component

        Args:
            venue: 
                venue of the document 
            year: 
                year of the document 
            docname: 
                document name of the document 
            doc_start_char: 
                starting character offset of the entity in the document 
            doc_end_char:
                ending character offset of the entity in the document 
            text:
                text of the entity 
            ner_label: 
                ner label of the entity 
            sent_toks:
                list of words of the sentence that contains the entity 
            sentid:
                sent index of the sentence that contains the entity 
            sent_start_idx:
                the starting word index of the entity in the sentence
            sent_end_idx:
                the ending word index of the entity in the sentence
        """
    
        self.venue = venue 
        self.year = year 
        self.docname = docname

        self.doc_id = "%s_%s_%s" % (venue, year, docname)
        self.span_id = "%s-%s-%s" % (self.doc_id, str(doc_start_char), str(doc_end_char))
        self.doc_start_char = doc_start_char
        self.doc_end_char = doc_end_char
        self.text = text
        self.ner_label = ner_label
        self.std_text = old_canonical_target_name(self.text) if self.ner_label == "Target" else canonical_component_name(self.text)
        self.sent_toks = sent_toks
        self.sentid = sentid
        self.sent_start_idx = sent_start_idx
        self.sent_end_idx = sent_end_idx
        self.span_width = len(self.text.split())
        self.bert_start_idx = None # location of < of <e>
        self.bert_end_idx = None
        self.relation_label = None

    def insert_type_markers(self, tokenizer, use_std_text = True, max_len = 512):
        """
            This function inserts type markers such as <Target> around the entity in the sentence 

            use_std_text: whether to substitute the entity's text with its canonical name in the sentence. for example, 
            if use_std_text is true, then the sentence 'A contains K' would be turned into 'A contains <T>Potassium<\\T>'
        """
        assert self.sent_toks is not None


        self.input_ids = []
        exceed_leng = 0 

        prespans = tokenizer.tokenize(" ".join(["[CLS]"] + self.sent_toks[:self.sent_start_idx]))
        start_markers = ["<ner_start=%s>" % (self.ner_label.lower())]
        if use_std_text:
            spans = tokenizer.tokenize(self.std_text)
        else:
            spans = tokenizer.tokenize(" ".join(self.sent_toks[self.sent_start_idx:self.sent_end_idx]))

        end_markers = ["<ner_end=%s>" % (self.ner_label.lower())]

        posspans = tokenizer.tokenize(' '.join(self.sent_toks[self.sent_end_idx:] + ["[SEP]"]))

        if len(prespans + start_markers + spans + end_markers + posspans) > max_len:
            # truncate now 
            diff = len(prespans + start_markers + spans + end_markers + posspans) - max_len

            prepsans, posspans, diff = truncate(prespans, posspans, diff)

        self.input_ids = tokenizer.convert_tokens_to_ids(prespans + start_markers + spans + end_markers + posspans)
        self.bert_start_idx = len(prespans)
        self.bert_end_idx = len(prespans + start_markers + spans)

        # assert tokenizer.convert_ids_to_tokens(self.input_ids)[self.bert_start_idx] == f"<ner_start={self.ner_label.lower()}>" and  tokenizer.convert_ids_to_tokens(self.input_ids)[self.bert_end_idx] == f"<ner_end={self.ner_label.lower()}>"

        # if input_ids is longger than the maximum length, simply use the 0th vector to represent the entity 
        if len(self.input_ids) > max_len:
            exceed_leng = 1
            self.input_ids = self.input_ids[: max_len]
            
            if self.bert_start_idx >= max_len:
                self.bert_start_idx = 0
            
            if self.bert_end_idx >= max_len:
                self.bert_end_idx = 0
        
        return exceed_leng



# ============ Inference Utils ===========
def old_canonical_target_name(name):
    """
    Gets canonical target name: title case, replace spaces and dashes
    with underscore.  Aliases are expanded using tagettab.
    :param name - name whose canonical name is to be looked up
    :return canonical name
    """
    name = name.strip()
    # Remove whitespace, dashes, and underscores
    strip_ws = re.sub(r'[\s_-]+', ' ', name)
    # Use capwords so e.g. Bear's Lodge does not become Bear'S Lodge
    # and replace spaces with underscores in final version
    name = string.capwords(strip_ws).replace(' ', '_')
    
    if name in targettab:

        return targettab[name].decode('utf8')
    else:
        return name



def get_sent2entities(targets, components):
    """
     put targets and components to the corresponding sentence
    """
    sent2entities = {}
    # map to sentence 
    for t in targets:
        sentid = "%s,%s,%s,%s" % (t.venue,t.year,t.docname,str(t.sentid))
        if sentid not in sent2entities:
            sent2entities[sentid] = {
                "Targets":[],
                "Components":[]
            }
        sent2entities[sentid]['Targets'].append(deepcopy(t))
    for c in components:
        sentid = "%s,%s,%s,%s" % (c.venue,c.year,c.docname,str(c.sentid))
        if sentid not in sent2entities:
            sent2entities[sentid] = {
                "Targets":[],
                "Components":[]
            }
        sent2entities[sentid]['Components'].append(deepcopy(c))

    return sent2entities
def get_word_dist(idx1, idx2):
    """
    get distance between two index tuples. Each index tuple contains (starting index, ending index)
    """
    dist = None
    for k in idx1:
        for j in idx2:
            curdist = abs(k - j)
            if dist is None:
                dist = curdist
            else:
                dist = min(dist, curdist)
    return dist

def get_closest_target_or_container(targets, components, mode = "container"):


    """
    Link each containee to its closest target/container in the same sentence. 

    Argument: 
        targets: a list of target entities
        components: a list of component entities
        mode: can only be "container" or "target". This is to indicate whether to get the closest target or the closest container instance. 
    """

    mode = mode.lower()

    if mode not in ['container', 'target']:
        raise NameError("Invalid mode: %s. The only possible choices are 'container' and 'target' " % (mode))

    sent2entities = get_sent2entities(targets, components)

    new_rels = []
    for sentid in sent2entities:
        components, targets = sent2entities[sentid]['Components'], sent2entities[sentid]['Targets']
        
        for component in components:
            if component.pred_relation_label != 'Contains':
                continue

            cidx = (component.sent_start_idx, component.sent_end_idx)
            closest_targetid = None
            closest_tidx = None
            min_dist = None
            
            # find closest target/container and assign
            for target in targets:
                if mode == 'container' and target.pred_relation_label != 'Contains':
                    continue
                tidx = (target.sent_start_idx, target.sent_end_idx) 
                dist = get_word_dist(cidx, tidx)
                is_closest = False
                if min_dist is None: 
                    is_closest = 1
                elif dist < min_dist: 
                    is_closest = 1
                elif dist == min_dist:
                    # If there is a tie, choose the preceding target
                    is_closest = closest_tidx[0] > tidx[0]
                if is_closest:
                    min_dist = dist
                    closest_targetid = target.span_id
                    closest_tidx = tidx

            if closest_targetid is None: continue

            for target in targets:
                if target.span_id == closest_targetid:
                    new_rels.append((target, component))

    return new_rels


def get_closest_component_or_containee(targets, components, mode = 'containee'):

    """
    Link each container to its closest component/containee in the same sentence. 

    Argument: 
        targets: a list of target entities
        components: a list of component entities
        mode: can only be "containee" or "component". This is to indicate whether to get the closest containee or the closest component instances.
    """

    mode = mode.lower()

    if mode not in ['containee', 'component']:
        raise NameError("Invalid mode: %s. The only possible choices are 'containee' and 'component' " % (mode))
    sent2entities = get_sent2entities(targets, components)

    new_rels = []
    for sentid in sent2entities:
        components, targets = sent2entities[sentid]['Components'], sent2entities[sentid]['Targets']
        for target in targets:
            if target.pred_relation_label != 'Contains': 
                continue
            tidx = (target.sent_start_idx, target.sent_end_idx)
            closest_cidx = None
            min_dist = None

            # find closest target and assign
            for component in components:
                if mode == 'containee' and component.pred_relation_label != 'Contains':
                    continue
                cidx = (component.sent_start_idx, component.sent_end_idx) 
                dist = get_word_dist(cidx, tidx)
                is_closest = False
                if min_dist is None: 
                    is_closest = 1
                elif dist < min_dist: 
                    is_closest = 1
                elif dist == min_dist:
                    # break tie by choosing the following component 
                    is_closest = closest_cidx[0] < cidx[0]

                if is_closest:
                    min_dist = dist
                    closest_cidx = cidx

            if closest_cidx is None: continue
            for component in components:
                if component.sent_start_idx == closest_cidx[0]:
                  new_rels.append((target, component))

    return new_rels

def get_closest_target_and_component(targets, components):

    rels1 = get_closest_component_or_containee(deepcopy(targets),deepcopy(components), mode = 'component')
    rels2 = get_closest_target_or_container(deepcopy(targets), deepcopy(components), mode = 'target')

    seen_rel = set()
    new_rels = []
    for t, c in rels1 + rels2:
        if (t.span_id, c.span_id) in seen_rel:
          continue
        seen_rel.add((t.span_id, c.span_id))
        new_rels.append((t,c))
    
    return new_rels

def get_closest_container_and_containee(targets, components):

    rels1 = get_closest_component_or_containee(deepcopy(targets),deepcopy(components), mode = 'containee')
    rels2 = get_closest_target_or_container(deepcopy(targets), deepcopy(components), mode = 'container')

    seen_rel = set()
    new_rels = []
    for t, c in rels1 + rels2:
        if (t.span_id, c.span_id) in seen_rel:
          continue
        seen_rel.add((t.span_id, c.span_id))
        new_rels.append((t,c))
    
    return new_rels



# ============== PARSER ===========
class UnaryParser(CoreNLPParser): 
    """ Relation extraction using unary classifiers. The unaryParser class depends on
    the outputs provided by the CoreNLPParser class.
    """

    def __init__(self, corenlp_server_url, ner_model_file, containee_model_file, container_model_file, gpu_id = 0 ):
        """
        Args:
            containee_model_file: 
                pretrained model file (.ckpt) for Containee 
            
            container_model_file:
                pretrained model file (.ckpt) for Container  
            
            gpu_id:
                id of GPU. Negative gpu_id means no GPU to be used. 
        """

        super(UnaryParser, self).__init__(corenlp_server_url,ner_model_file,'jsre_parser')

        self.corenlp_server_url = corenlp_server_url
        self.ner_model_file = ner_model_file
        self.containee_model_file = containee_model_file
        self.container_model_file = container_model_file
        self.containee = None 
        self.container = None 
        self.gpu_id = gpu_id

        logger = logging.getLogger('py.warnings')

        logger.info('Loading pretrained Containee')
        self.containee =  to_device(self.load_unary_model('Containee'), self.gpu_id)
        self.containee.eval()


        logger.info('Loading pretrained Container')
        self.container = to_device(self.load_unary_model('Container'), self.gpu_id)
        self.container.eval()


    def load_unary_model(self, model_name):
        """ Load pretrained Container and Containee model"""
        
        model = Model(model_name, gpu_id = self.gpu_id)
        if model_name == 'Container':
            if self.gpu_id < 0: 
                model.load_state_dict(torch.load(self.container_model_file, map_location=torch.device('cpu')))
            else:
                model.load_state_dict(torch.load(self.container_model_file))
        else:
            if self.gpu_id < 0: 
                model.load_state_dict(torch.load(self.containee_model_file, map_location = torch.device('cpu')))
            else:
                model.load_state_dict(torch.load(self.containee_model_file))

        return model 

    def predict(self, model, dataloader):
        
        pred_instances = []
        soft = torch.nn.Softmax(dim = 1)
        
        with torch.no_grad():
            for i, item in enumerate(dataloader):
                logits =model.forward(item)
                scores = soft(logits).cpu().numpy()
                y_preds = np.argmax(scores,1)

                for ins, y_pred, score in zip(item["instances"], y_preds, scores):
                    if score[0] > 0.5:
                        y_pred = 0
                    else:
                        y_pred = 1
                    ins.pred_relation_label = ind2label[y_pred]
                    ins.pred_score = score
                    pred_instances.append(ins)

        return pred_instances

    def add_entities(self, queue, e):
        # add entities and merge entities if possible. Merge entities when two words have the same ner label that is not 'O' and (adjacent or two words are separated by hyphens or underscores). Note that this method is not perfect since we always merge adjacent words with the same NER into an entity, thus will lose a lot of smaller entities. For example, we will get only "Iron - Feldspar" and miss "Iron" and "Feldspar"

        if not len(queue) or e['label'] == 'O':
            queue.append(deepcopy(e))
            return 
        last_e = queue[-1]
        if last_e['label'] == e['label']:
            # merge 
            last_e['text'] = "%s %s" % (last_e['text'], e['text'])
            last_e['doc_end_char'] = e['doc_end_char']
            last_e['sent_end_idx'] = e['sent_end_idx']
        else:
            if len(queue) > 1 and queue[-1]['text'] in ["_", "-"] and queue[-2]['label'] == e['label']: # words that are splitted by hyphen or underscores
                queue[-2]['text'] = "%s%s%s" % (queue[-2]['text'],last_e['text'],e['text'])
                queue[-2]['doc_end_char'] = e['doc_end_char']
                queue[-2]['sent_end_idx'] = e['sent_end_idx']
                queue.pop(-1)
            else:
                queue.append(deepcopy(e))

    def extract_entities(self, doc, use_component = True):

        entities = []

        for sent in doc['sentences']:
            sentid = int(sent["index"])
            sent_entities = []
            for tokidx, token in enumerate(sent['tokens']):
                entity = {
                "text": token["word"],
                "doc_start_char": token["characterOffsetBegin"],
                "doc_end_char": token["characterOffsetEnd"],
                "sent_start_idx": int(tokidx),
                "sent_end_idx": int(tokidx) + 1,
                "sentid": int(sentid),
                "label": token['ner']
                }
                self.add_entities(sent_entities, entity)
            if use_component:
                # if use_component is true, then adjacent element and minerals should also be merged 
                for e in sent_entities:
                    if e['label'] in ['Element', 'Mineral']:
                        e['label'] = 'Component'

                new_sent_entities = []
                for tokidx, token in enumerate(sent['tokens']):
                    entity = {
                    "text": token["word"],
                    "doc_start_char": token["characterOffsetBegin"],
                    "doc_end_char": token["characterOffsetEnd"],
                    "sent_start_idx": int(tokidx),
                    "sent_end_idx": int(tokidx) + 1,
                    "sentid": int(sentid),
                    "label": 'Component' if token['ner'] in ['Element', 'Mineral'] else token['ner'] 
                    }
                    self.add_entities(new_sent_entities, entity)

                new_sent_entities = new_sent_entities + sent_entities
                sent_entities = []

                # remove duplicate entities generated in two passes
                seen_id = set()
                for e in new_sent_entities:
                    entity_id = "%s %s" % (str(e['doc_start_char']), str(e['doc_end_char']))
                    if entity_id not in seen_id:
                        sent_entities.append(e)
                        seen_id.add(entity_id)

            entities.extend([e for e in sent_entities if e['label'] != 'O'])

        for e in entities:
            if e['label'] == 'Target':
                e['std_text'] = old_canonical_target_name(e['text'])
            elif e['label'] in ['Element', 'Mineral', 'Component']:
                e['std_text'] = canonical_component_name(e['text'])

        return entities


    def parse(self, text, batch_size = 10, entity_linking_method = 'closest_container_closest_containee'): 
        
        """
        Args:
            text:   
                text of the document 

            batch_size:
                batch size at prediction time.

            entity_linking_method:
                strategy to form Contains relations from Targets and Components.  
                
                Options:
                    closest_containee:
                        for each Container instance, link it to its closest Containee instance with a Contains relation
                    closest_container:
                        for each Containee instance, link it to its closest Container instance with a Contains relation
                    closest_component:
                        for each Container instance, link it to its closest Component instance with a Contains relation,
                    closest_target:
                        for each Containee instance, link it to its closest Target instance with a Contains relation
                    union_closest_containee_closest_container:
                        union the relation instances found by closest_containee and closest_container
        """

        entity_linking_methods = [
            'closest_container_closest_containee',
            'closest_target_closest_component'
            'closest_containee',
            'closest_container',
            'closest_component',
            'closest_target'
        ]

        entity_linking_method = entity_linking_method.lower()
        if entity_linking_method not in entity_linking_methods:
            raise NameError("Unrecognized entity linking method: %s. You need to choose from [%s] !" % (entity_linking_method, ', '.join(entity_linking_methods)))
        
        corenlp_dict = super(UnaryParser, self).parse(text)


        entities = [e for e in self.extract_entities(corenlp_dict, use_component = True) if e['label'] in ['Target', 'Component']]

        num_target = len([ e for e in entities if e['label'] == 'Target'])
        num_component = len([e for e in entities if e['label'] == 'Component'])

        logger = logging.getLogger('py.warnings')


        logger.info('Extracted %d Targets and %d Components' % (num_target, num_component))

        # map extracted component and target entities to their corresponding sentences
        sentid2entities = {}
        for e in entities:
            sentid = e['sentid']
            if e['label'] not in ['Target', 'Component']:
                continue

            if sentid not in sentid2entities:
                sentid2entities[sentid] = []
            sentid2entities[sentid].append(e)

        # make target and component instances for inference. Here we only make inference for Target/Component that co-occurs with some other Component/Target in the same sentence. If the sentence has only components or targets, we assume that there wouldn't be any within-sentence Contains relations in this sentence. As a result, the entities in this sentence wouldn't be taken as an inference candidate for Container and Containee. 
        target_instances = []
        component_instances = [] 
        exceed_len_cases = 0 
        for sentid, sent_entities in sentid2entities.items():
        
            possible_entity_labels = set([e['label'] for e in sent_entities])   
            if 'Target' not in possible_entity_labels or 'Component' not in possible_entity_labels:
                continue 

            sent_toks = [token['word'] for token in corenlp_dict['sentences'][sentid]['tokens']]

            seen_spanids = set() # used to remove duplicates in case
            for e in sent_entities:
                # e doesn't have any venue, year and docname, since they are not provided in the arguments. So just assign a 'None' to these. 
                span = Span_Instance('None', 'None', 'None', e['doc_start_char'], e['doc_end_char'], e['text'], e['label'], sent_toks = deepcopy(sent_toks), sentid = sentid, sent_start_idx = e['sent_start_idx'], sent_end_idx = e['sent_end_idx'])

                # insert type markers 
                if span.span_id not in seen_spanids:
                    tokenizer = self.containee.tokenizer if e['label'] == 'Component' else self.container.tokenizer 
                    exceed = span.insert_type_markers(tokenizer, max_len = 512) # insert entity markers around the entity in its sentence, convert the sentence to token ids and check if the insertion makes the number of token ids more than 512

                    if e['label'] == 'Target':
                        target_instances.append(span)
                    else:
                        component_instances.append(span)
                    exceed_len_cases += exceed

        logger.info('Collected %d Targets and %d Components that co-occur with Components/Targets in the same sentence for relation inference.' % (len(target_instances), len(component_instances)))
        logger.info('%d of them exceed 512 tokens after inserting entity markers in the sentences.' % (exceed_len_cases))

        # make dataset the model takes for prediction
        target_dataset = MyDataset(target_instances)
        component_dataset = MyDataset(component_instances)

        target_dataloader = DataLoader(target_dataset, batch_size = batch_size, collate_fn = collate)
        component_dataloader = DataLoader(component_dataset, batch_size= batch_size, collate_fn = collate)

        # Inference using Container and Containee
        target_preds = self.predict(self.container, target_dataloader)
        component_preds = self.predict(self.containee, component_dataloader)

        contains_relations = self.form_relations(target_preds, component_preds, corenlp_dict, entity_linking_method)

        return {
            'ner': corenlp_dict['ner'],
            'sentences': corenlp_dict['sentences'],
            'relation': contains_relations,
            'X-Parsed-By': 'UnaryParser:' + entity_linking_method 
        }

    def form_relations(self, target_preds, component_preds, corenlp_dict, entity_linking_method):

        if entity_linking_method == 'closest_component':
            rels = get_closest_component_or_containee(target_preds, component_preds, mode = 'component')
        if entity_linking_method == 'closest_containee':
            rels = get_closest_component_or_containee(target_preds, component_preds, mode = 'containee')
        if entity_linking_method == 'closest_target':
            rels = get_closest_target_or_container(target_preds, component_preds, model = 'target')
        if entity_linking_method == 'closest_container':
            rels = get_closest_target_or_container(target_preds, component_preds, model = 'container')

        if entity_linking_method == 'closest_container_closest_containee':
            rels = get_closest_container_and_containee(target_preds, component_preds)

        if entity_linking_method == 'closest_target_closest_component':
            rels = get_closest_target_and_component(target_preds, component_preds)

        contains_relations = []
        for target, component in rels: 
            sentid = target.sentid
            contains_relations.append({
                'label': 'contains',
                # std text in the following means canonical texts (texts processed by canonical_target_name or canonical_component_name)
                'target_names': [target.std_text],
                'cont_names': [component.std_text],
                'target_ids': ['%s_%d_%d' % (target.ner_label.lower(),
                                             target.doc_start_char,
                                             target.doc_end_char)],
                'cont_ids': ['%s_%d_%d' % (component.ner_label.lower(),
                                           component.doc_start_char,
                                           component.doc_end_char)],
                'sentence':  ' '.join([t['originalText']
                                       for t in corenlp_dict['sentences'][sentid]['tokens']]),
                'source': 'UnaryParser:'+entity_linking_method
            })
        return contains_relations

def process(in_file, in_list, out_file, log_file, tika_server_url, ads_url, ads_token, corenlp_server_url, ner_model, containee_model_file, container_model_file, entity_linking_method, gpu_id, batch_size): 

    # Log input parameters
    logger = LogUtil(log_file)
    logger.info('Input parameters')
    logger.info('in_file: %s' % in_file)
    logger.info('in_list: %s' % in_list)
    logger.info('out_file: %s' % out_file)
    logger.info('log_file: %s' % log_file)
    logger.info('tika_server_url: %s' % tika_server_url)
    logger.info('ads_url: %s' % ads_url)
    logger.info('ads_token: %s' % ads_token)
    logger.info('corenlp_server_url: %s' % corenlp_server_url)
    logger.info('ner_model: %s' % os.path.abspath(ner_model))
    logger.info('container_model_file: %s' % os.path.abspath(container_model_file))
    logger.info('containee_model_file: %s' % os.path.abspath(containee_model_file))
    logger.info('entity_linking_method: %s' % entity_linking_method)
    logger.info('gpu_id: %s' % str(gpu_id))
    
    if in_file and in_list:
        raise NameError('[ERROR] in_file and in_list cannot be provided simultaneously')

    ads_parser = AdsParser(ads_token, ads_url, tika_server_url)

    unary_parser = UnaryParser(corenlp_server_url, ner_model, containee_model_file, container_model_file, gpu_id = gpu_id)

    if in_file:
        files = [in_file]
    else:
        files = read_lines(in_list)

    out_f = open(out_file, 'wb', 1)
    for f in tqdm(files):
        try:
            ads_dict = ads_parser.parse(f)

            unary_dict = unary_parser.parse(ads_dict['content'], batch_size = batch_size, entity_linking_method = entity_linking_method)

            ads_dict['metadata']['ner'] = unary_dict['ner']
            ads_dict['metadata']['rel'] = unary_dict['relation']
            ads_dict['metadata']['sentences'] = unary_dict['sentences']
            ads_dict['metadata']['X-Parsed-By'].append(unary_dict['X-Parsed-By'])

            out_f.write(json.dumps(ads_dict))
            out_f.write('\n')
        except Exception as e:
            logger.info('Unary parser failed: %s' % abspath(f))
            logger.error(e)

    out_f.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    input_parser = parser.add_mutually_exclusive_group(required=True)

    input_parser.add_argument('-i', '--in_file', help='Path to input file')
    input_parser.add_argument('-li', '--in_list', help='Path to input list')
    parser.add_argument('-o', '--out_file', required=True,
                        help='Path to output JSON file')
    parser.add_argument('-l', '--log_file', default='./unary-parser-log.txt',
                        help='Log file that contains processing information. '
                             'It is default to ./unary-parser-log.txt unless '
                             'otherwise specified.')
    parser.add_argument('-p', '--tika_server_url', required=False,
                        help='Tika server URL')
    parser.add_argument('-a', '--ads_url',
                        default='https://api.adsabs.harvard.edu/v1/search/query',
                        help='ADS RESTful API. The ADS RESTful API should not '
                             'need to be changed frequently unless someting at '
                             'the ADS is changed.')
    parser.add_argument('-t', '--ads_token',
                        default='jON4eu4X43ENUI5ugKYc6GZtoywF376KkKXWzV8U',
                        help='The ADS token, which is required to use the ADS '
                             'RESTful API. The token was obtained using the '
                             'instructions at '
                             'https://github.com/adsabs/adsabs-dev-api#access. '
                             'The ADS token should not need to be changed '
                             'frequently unless something at the ADS is '
                             'changed.')
    parser.add_argument('-c', '--corenlp_server_url',
                        default='http://localhost:9000',
                        help='CoreNLP Server URL')
    parser.add_argument('-n', '--ner_model', required=False,
                        help='Path to a Named Entity Recognition (NER) model')
    
    parser.add_argument('-cnte', '--containee_model_file',
                    required = True,
                    help='Path to a trained Containee model')
    parser.add_argument('-cntr', '--container_model_file',
                    required = True,
                    help='Path to a trained Container model')
    parser.add_argument('-m', '--entity_linking_method',
                    required = True,
                    choices = [
                        'closest_container_closest_containee',
                        'closest_target_closest_component',
                        'closest_containee',
                        'closest_container',
                        'closest_component',
                        'closest_target'
                    ],
                    help='Method to form relations between entities. '
                    '[closest_containee]: for each Container instance, link it to its closest Containee instance with a Contains relation, '
                    '[closest_container]: for each Containee instance, link it to its closest Container instance with a Contains relation, '
                    '[closest_component]: for each Container instance, link it to its closest Component instance with a Contains relation, '
                    '[closest_target]: for each Containee instance, link it to its closest Target instance with a Contains relation, '
                    '[closest_target_closest_component]: union the relation instances found by closest_target and closest_component, '
                    '[closest_container_closest_containee]: union the relation instances found by closest_containee and closest_container. This is the best method on the MTE test set')

    parser.add_argument('-g', '--gpu_id',
                    default = 0,
                    type = int,
                    help='GPU ID. If set to negative then no GPU would be used.')
    parser.add_argument('-b', '--batch_size',
                    default = 10,
                    type = int, 
                    help='Batch size at inference time.')

    args = parser.parse_args()
    process(**vars(args))
