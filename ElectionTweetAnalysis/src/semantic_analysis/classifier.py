'''
classifier.py
@author: Bolun Huang
@change: Feb 2014@modifying the structure
Classification of campaigners, supporters and neutral users from Election Tweets
'''
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn import tree
from sklearn import metrics
from pymongo import Connection
import random
import cjson

class UserClassifier:
	DB_SERVER = "localhost"
	DB_PORT = 27017
	DB_NAME = "electiontweetsanalysis"
	COLLECTION_UV = "user_profile"
	def __init__(self, alpha = 0.8):
		self.alpha = alpha

		self.connection = Connection(self.DB_SERVER, self.DB_PORT)
		self.db = self.connection[self.DB_NAME]
		
		self.features = ["interval_variance", "retweet_ratio", 
						"url_ratio", "unique_mention", "unique_url"]
		
		self.vector = {}
		f = open("data/labelled_user_new.txt","r")
		for line in f:
			if not line.startswith("#"):
				line = line.split(" ")
				label = 0
				if line[2] == "r":
					label = 1
				self.vector.update({line[0].strip() : {}})
		f.close()
		for user in self.vector:
			it = self.db[self.COLLECTION_UV].find({'screen_name': user})
			for i in it:
				self.vector[user].update({key : i[key] for key in self.features})
		#print self.vector

		self.data_ids = self.vector.keys()
		random.shuffle(self.data_ids)
		self.train_ids = []
		self.test_ids = []
		
		# TODO: load different set of features
		#f = open("results/features_top5.json","r")
		#self.features = cjson.decode(f.readline())
		print self.features

	
	def get_X_y(self, test_only=False):
		if not test_only:
			#training data
			X_tr, y_tr = [], []
			for user in self.train_ids:
				v = []
				for t in self.features:
					v.append(self.vector[user][t])
				X_tr.append(v)
				
			for user in self.train_ids:
				it = self.db[self.COLLECTION_UV].find({"screen_name" : user})
				for i in it:
					y_tr.append(i['class'])
			#print len(X_tr), len(y_tr)

		#test data
		X_te, y_te = [], []
		for user in self.test_ids:
			v = []
			for t in self.features:
				v.append(self.vector[user][t])
			X_te.append(v)
		
		for user in self.test_ids:
			it = self.db[self.COLLECTION_UV].find({"screen_name" : user})
			for i in it:
				y_te.append(i['class'])
		
		#print len(X_te), len(y_te)

		if test_only:
			return {'train': {'X': self.train_data['X'], 'y': self.train_data['y']}, 'test': {'X': X_te, 'y': y_te}}
		else:
			return {'train': {'X': X_tr, 'y': y_tr}, 'test': {'X': X_te, 'y': y_te}}

	def initialize_data(self, test_only=False):
		X_y_dict = self.get_X_y(test_only)
		if not test_only:
			self.train_data = X_y_dict['train']
		self.test_data = X_y_dict['test']

	def train(self):
		### decision tree model
		self.clf = tree.DecisionTreeClassifier()
		self.clf = self.clf.fit(self.train_data['X'], self.train_data['y'])
		out = tree.export_graphviz(self.clf, out_file='data/decision_tree_normal_%.1f.dot' %self.alpha, feature_names=self.features)
		out.close()
		### naive bayes model
		#self.clf_2 = GaussianNB()
		#self.clf_2.fit(self.train_data['X'], self.train_data['y'])
	
	def prediction(self):
		print "*******decision tree model********"
		y_predicted = self.clf.predict(self.test_data['X'])
		#print self.clf.score(self.test_data['X'], self.test_data['y'])
		
		#y_predicted_prob = self.clf.predict_proba(self.test_data['X'])
		#print len(y_predicted), len(self.test_data['y'])
		f_score = metrics.f1_score(self.test_data['y'], y_predicted)
		accuracy = metrics.accuracy_score(self.test_data['y'], y_predicted)
		print "f1-score:   %0.3f" % f_score
		print "accuracy:   %0.3f" % accuracy
		#for i in range(0, len(self.test_data['y'])):
		#	print self.test_data['y'][i],
		#for i in range(0, len(y_predicted)):
		#	print y_predicted[i],
		#print "classification report:"
		#print metrics.classification_report(self.test_data['y'], y_predicted, target_names=['democrat','republican'])
		#print metrics.classification_report(self.test_data['y'], y_predicted, target_names=['other', 'journalist',''])
		return [f_score, accuracy]

	def cross_validate(self, fold = 10):
		"""
		Implement cross validation given the number of folds
		It first shuffle the ids and partition the id according
		to the given fold number
		@param fold: number of fold
		"""
		f_scores = []
		accuracies = []
		random.shuffle(self.data_ids)
		data_size = len(self.data_ids)
		trunk_size = data_size/fold;
		for test in range(fold):
			self.train_ids = []
			self.test_ids = []
			# plitting the data
			for j in range(fold):
				if j == test and j != fold - 1:
					self.test_ids.extend(self.data_ids[j*trunk_size:(j+1)*trunk_size])
				elif j == test and j == fold - 1:
					self.test_ids.extend(self.data_ids[j*trunk_size:len(self.data_ids)])
				elif j != test and j != fold - 1:
					self.train_ids.extend(self.data_ids[j*trunk_size:(j+1)*trunk_size])
				elif j != test and j == fold - 1:
					self.train_ids.extend(self.data_ids[j*trunk_size:len(self.data_ids)])
			
			print "train:", len(self.train_ids), " test:", len(self.test_ids)
			#print self.test_ids
			self.initialize_data()
			self.train()
			result = self.prediction()
			f_scores.append(result[0])
			accuracies.append(result[1])
		return [sum(f_scores)/float(len(f_scores)), sum(accuracies)/float(len(accuracies))]

	def test(self,ids_to_test):
		self.test_ids = ids_to_test
		self.initialize_data(False)
		y_predicted = self.clf.predict(self.test_data['X'])
		#print y_predicted
		return y_predicted


def main():
    #alphas = [0.1, 0.5, 0.8, 0.9, 1.0]
    #alphas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    alphas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 0.91, 0.92, 0.93, 0.94, 0.95, 0.96, 0.97, 0.98, 0.99]

    folds = [4, 5, 10]
    Iter = 10 # conduct Iter times cross validation
    f_scores = []
    accuracies = []
    for a in alphas:
        uc = UserClassifier(alpha = a)
        print "*****************************************************"
        print "CROSS VALIDATION RESULT for alpha value = %.2f" %a
        #uc.initialize_data()
        #uc.train()
        #uc.prediction()
        tuple_f = []
        tuple_s = []
        for f in folds:
            score = []
            accuracy = []
            print "%d FOLD CROSS VALIDATION.........................." %f
            for i in range(Iter):
                result = uc.cross_validate(fold = f)
                score.append(result[0])
                accuracy.append(result[1])
            print ""
            tuple_f.append(sum(score)/float(len(score)))
            tuple_s.append(sum(accuracy)/float(len(accuracy)))
        f_scores.append(tuple_f)
        accuracies.append(tuple_s)
        print "\t\t"

    f1 = open("results/results_fscore_accuracy_feb15/f_scores_0.1-1.0_5.csv","w")
    f2 = open("results/results_fscore_accuracy_feb15/accuracy_0.1-1.0_5.csv","w")
    f1.write("alpha,4fold,5fold,10fold\n")
    f2.write("alpha,4fold,5fold,10fold\n")
    for i in range(len(alphas)):
        s = str(alphas[i]) + ","
        for j in range(len(f_scores[i])):
            if j != len(f_scores[i]) - 1:
                s = s + str(f_scores[i][j]) + ","
            else:
                s = s + str(f_scores[i][j]) + "\n"
        f1.write(s)
        s = ""
        s = str(alphas[i]) + ","
        for j in range(len(accuracies[i])):
            if j != len(accuracies[i]) - 1:
                s = s + str(accuracies[i][j]) + ","
            else:
                s = s + str(accuracies[i][j]) + "\n"
        f2.write(s)
    f1.close()
    f2.close()

if __name__ == "__main__":
	main()
