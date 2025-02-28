# -*- coding: utf-8 -*-
"""
根据之前的分类结果，这里使用SVM-RFECV选择分类特征，并且保存模型结果，用于之后对新数据的分类
"""

import subprocess
import sys
import os
import pandas as pd
import openpyxl
import joblib
from sklearn.svm import SVC
from sklearn.feature_selection import RFECV
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold

# 定义一个检查并安装库的函数
def install_and_import(package, import_name=None):
    try:
        if import_name is None:
            import_name = package
        __import__(import_name)
    except ImportError:
        print(f"{package} 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        globals()[import_name] = __import__(import_name)
    else:
        globals()[import_name] = __import__(import_name)

# 检查并安装所需的库
required_packages = {
    'pandas': None,        
    'openpyxl': None,      
    'scikit-learn': 'sklearn'
}

for package, import_name in required_packages.items():
    install_and_import(package, import_name)

# 定义基础路径
abideDir = 'E:/PhDproject/ABIDE'  
resDir = os.path.join(abideDir, "Analysis", "Cluster", "Spect618")
plotDir = os.path.join(abideDir, "Plot", "Cluster", "Spect618")
newDate = "240610"

# 读取Excel文件
cluster_file = os.path.join(resDir, f"Cluster_{newDate}.csv")
data = pd.read_csv(cluster_file)

# 分离分类标签 (clusterID) 和特征 (bankssts之后的列)
X = data.loc[:, 'bankssts':] 
y = data['clusterID']         

# 划分训练集和测试集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=941205)

# 定义初始线性SVM作为基模型，用于第一次RFECV
svc = SVC(kernel="linear")

# 使用RFECV进行递归特征消除并自动选择最优特征数量
rfecv = RFECV(estimator=svc, step=1, cv=StratifiedKFold(5), scoring='accuracy')
rfecv.fit(X_train, y_train)

# 输出最佳特征数量和被选中的特征
print(f"最佳特征数量: {rfecv.n_features_}")
selected_features = X.columns[rfecv.support_]
print("被选中的特征: ", selected_features)

# 使用选出的特征
X_train_selected = X_train[selected_features]
X_test_selected = X_test[selected_features]

# 定义参数网格，包含所有常用的核函数
param_grid = {
    'C': [0.1, 1, 10, 100],         
    'gamma': [1, 0.1, 0.01, 0.001], 
    'kernel': ['linear', 'rbf', 'poly', 'sigmoid']
}

# 使用GridSearchCV对选出的特征进行超参数优化
grid = GridSearchCV(SVC(), param_grid, refit=True, verbose=2)
grid.fit(X_train_selected, y_train)

# 输出最佳参数
print(f"最佳参数: {grid.best_params_}")

# 使用网格搜索找到的最佳 kernel 重新进行特征选择
best_kernel = grid.best_params_['kernel']
svc_best_kernel = SVC(kernel=best_kernel)

# 检查核类型，如果是线性核则使用RFECV，否则直接训练
if best_kernel == 'linear':
    rfecv_best_kernel = RFECV(estimator=svc_best_kernel, step=1, cv=StratifiedKFold(5), scoring='accuracy')
    rfecv_best_kernel.fit(X_train_selected, y_train)

    # 获取经过RFECV选择的特征
    selected_features_best = X_train_selected.columns[rfecv_best_kernel.support_]

    # 使用这些特征更新训练和测试数据集
    X_train_selected_best = X_train_selected[selected_features_best]
    X_test_selected_best = X_test_selected[selected_features_best]
else:
    print("非线性核使用最佳参数进行训练")
    X_train_selected_best = X_train_selected
    X_test_selected_best = X_test_selected

# 使用最佳参数进行重新训练和预测
svc_best_kernel.fit(X_train_selected_best, y_train)
y_pred_best = svc_best_kernel.predict(X_test_selected_best)

# 评估模型准确率
accuracy_best = accuracy_score(y_test, y_pred_best)
print(f"优化后的模型准确率: {accuracy_best:.2f}")

# 计算 F1 分数
f1_best = f1_score(y_test, y_pred_best, average='macro')
print(f"优化后的 F1 分数: {f1_best:.2f}")

# 保存训练好的模型
model_file = os.path.join(resDir, 'trained_svm_model.pkl')
joblib.dump(grid, model_file)
print(f"模型已保存到: {model_file}")

# 读取已保存的模型
loaded_model = joblib.load(model_file)

# 从已保存的GridSearchCV模型中提取最佳模型
best_model = loaded_model.best_estimator_

# 检查是否使用线性核，并获取特征权重
if best_model.kernel == 'linear':
    feature_weights = best_model.coef_[0]
    
    # 创建包含特征脑区和特征权重的数据框
    select_region = pd.DataFrame({
        'Region': selected_features_best,
        'Weight': feature_weights
    })
    
    # 按权重排序
    select_region = select_region.sort_values(by='Weight', ascending=False)
    
    # 输出排序后的特征脑区和权重
    print(select_region)
    
    # 保存结果到Excel文件
    output_file_select = os.path.join(resDir, 'select_region_sorted.xlsx')
    select_region.to_excel(output_file_select, index=False)
    print(f"结果已保存到: {output_file_select}")
else:
    print("使用的不是线性核，无法提取特征权重。")
